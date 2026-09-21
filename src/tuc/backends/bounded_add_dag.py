"""Explicit CPU-only Add/Bias extension of the frozen bounded DAG artifacts.

The original RFC 0319 files and non-Add emission stay unchanged. This boundary
accepts Add-containing graphs, reuses their data-only partition/residency checks,
and emits its own inspectable C11 primitives and schedule. It never executes.
"""

from __future__ import annotations

import gc
from dataclasses import fields
from math import prod
from types import MappingProxyType
from typing import cast

from tuc.backends import bounded_dag as legacy
from tuc.backends.bounded_dag import BoundedDAGArtifacts, DAGTarget
from tuc.backends.bounded_dag_codegen import KernelSpec, _body, _parameters
from tuc.ir.dialect import validate_hac_module_contract
from tuc.ir.dump import dump_module
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.modules import IRModule, IRStage
from tuc.runtime.partitioning import Assignment, CandidateScore, PartitionPlan
from tuc.runtime.residency import ResidencyPlan, ResidencySpace, plan_residency

SCHEMA_VERSION = "tuc.bounded_add_dag_artifacts.v0"
_KINDS = {"matmul": 0, "relu": 1, "sum_axis1": 2, "add": 3, "add_row_bias": 4}
_EVENTS = {"bind_input": 0, "copy": 1, "execute": 2, "publish_output": 3}
_RECORD_TYPES = (IRModule, ComputeGraph, ComputeOperation, TensorRef,
                 PartitionPlan, Assignment, CandidateScore, BoundedDAGArtifacts)
_Record = (IRModule | ComputeGraph | ComputeOperation | TensorRef |
           PartitionPlan | Assignment | CandidateScore | BoundedDAGArtifacts)


def _record(value: object, expected: type[_Record]) -> None:
    if type(value) is not expected or expected not in _RECORD_TYPES:
        raise ValueError("bounded Add record rejected")
    state = object.__getattribute__(value, "__dict__")
    keys = {item.name for item in fields(expected)}
    if (type(state) is not dict or len(state) != len(keys) or
            any(type(key) is not str for key in state) or set(state) != keys):
        raise ValueError("bounded Add record state rejected")


def _safe_metadata(value: object) -> None:
    """Prove exact dict backing before the legacy metadata visitor sees a proxy."""
    remaining = 4096

    def visit(item: object, depth: int) -> None:
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 8:
            raise ValueError("bounded Add metadata budget rejected")
        if type(item) is MappingProxyType:
            referents = gc.get_referents(item)
            if len(referents) != 1 or type(referents[0]) is not dict:
                raise ValueError("bounded Add metadata proxy rejected")
            item = referents[0]
        if type(item) is dict:
            if len(item) > 128 or any(type(key) is not str for key in item):
                raise ValueError("bounded Add metadata mapping rejected")
            for key, child in item.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif type(item) is tuple:
            if len(item) > 128:
                raise ValueError("bounded Add metadata sequence rejected")
            for child in item:
                visit(child, depth + 1)
        elif item is not None and type(item) not in (
                str, int, float, bool, LayoutKind, MemoryDomainKind):
            raise ValueError("bounded Add metadata type rejected")

    visit(value, 0)
    legacy._metadata(value)


def _add_operation(op: ComputeOperation, index: int) -> tuple[KernelSpec, int]:
    semantics = {key for key in op.attributes if not key.startswith("tuc.")}
    for key in legacy._BOOLEAN_HINTS.intersection(semantics):
        if type(op.attributes[key]) is not bool:
            raise ValueError("bounded Add hint rejected")
    semantics -= legacy._BOOLEAN_HINTS
    if "max_error_budget" in semantics:
        budget = op.attributes["max_error_budget"]
        if type(budget) not in (int, float) or cast(float, budget) < 0:
            raise ValueError("bounded Add error hint rejected")
        semantics.remove("max_error_budget")
    layout = op.attributes.get("tuc.layout")
    tile = op.attributes.get("tuc.layout_tile_shape")
    if (semantics != {"kernel"} or len(op.inputs) != 2 or
            type(layout) not in (str, LayoutKind) or layout != LayoutKind.ROW_MAJOR or
            type(tile) is not tuple or tile):
        raise ValueError("bounded Add semantics or layout rejected")
    lhs, rhs = (tensor.shape for tensor in op.inputs)
    out = op.outputs[0].shape
    if out != lhs:
        raise ValueError("bounded Add output shape rejected")
    if lhs == rhs:
        kind = "add"
    elif len(lhs) == 2 and rhs == (lhs[1],):
        kind = "add_row_bias"
    else:
        raise ValueError("bounded Add input shapes rejected")
    return KernelSpec(index, kind, (lhs, rhs), out), prod(out)


def _checked_graph(module: IRModule) -> tuple[tuple[KernelSpec, ...], tuple[int, ...]]:
    _record(module, IRModule)
    if (module.stage is not IRStage.HAC_IR or module.target is not None or
            type(module.metadata) is not dict):
        raise ValueError("bounded Add HAC-IR rejected")
    graph = module.graph
    _record(graph, ComputeGraph)
    legacy._name(graph.name)
    if (type(graph.operations) is not tuple or not 1 <= len(graph.operations) <= 8 or
            type(graph.metadata) is not MappingProxyType):
        raise ValueError("bounded Add graph rejected")
    _safe_metadata((module.metadata, graph.metadata))
    specs: list[KernelSpec] = []
    work: list[int] = []
    tensors: dict[str, TensorRef] = {}
    names: set[str] = set()
    for index, op in enumerate(graph.operations):
        _record(op, ComputeOperation)
        legacy._name(op.name)
        if (type(op.kind) is not OperationKind or type(op.inputs) is not tuple or
                type(op.outputs) is not tuple or not 1 <= len(op.inputs) <= 2 or
                len(op.outputs) != 1 or type(op.attributes) is not MappingProxyType or
                op.name in names):
            raise ValueError("bounded Add operation rejected")
        names.add(op.name)
        _safe_metadata(op.attributes)
        for tensor in (*op.inputs, *op.outputs):
            _record(tensor, TensorRef)
            legacy._tensor(tensor)
            previous = tensors.get(tensor.name)
            if previous is not None and (previous.shape != tensor.shape or
                                         previous.dtype != tensor.dtype):
                raise ValueError("bounded Add tensor identity rejected")
            tensors[tensor.name] = tensor
        if (op.kind is OperationKind.ELEMENTWISE and
                op.attributes.get("kernel") == "add"):
            spec, amount = _add_operation(op, index)
        else:
            spec, amount = legacy._operation(op, index)
        specs.append(spec)
        work.append(amount)
    if (len(tensors) > legacy.MAX_DAG_TENSORS or
            sum(work) > legacy.MAX_DAG_SCALAR_WORK or
            not any(spec.kind in ("add", "add_row_bias") for spec in specs)):
        raise ValueError("bounded Add graph budget or operation scope rejected")
    _safe_metadata((module.metadata, graph.metadata,
                    tuple(op.attributes for op in graph.operations)))
    validate_hac_module_contract(module)
    return tuple(specs), tuple(work)


def _partition(module: IRModule, partition: PartitionPlan,
               targets: dict[str, DAGTarget]) -> dict[str, ResidencySpace]:
    _record(partition, PartitionPlan)
    if (type(partition.assignments) is not tuple or
            len(partition.assignments) != len(module.graph.operations) or
            type(partition.candidate_scores) is not tuple or len(partition.candidate_scores) > 64 or
            type(targets) is not dict or len(targets) != 1):
        raise ValueError("bounded Add partition rejected")
    for name, target in targets.items():
        legacy._name(name, backend=True)
        if target is not DAGTarget.C11:
            raise ValueError("bounded Add supports selected CPU targets only")
    for edge_collection in (partition.transfer_edges, partition.layout_conversions,
                            partition.override_effects):
        if type(edge_collection) is not tuple or edge_collection:
            raise ValueError("bounded Add requires no transfers or overrides")
    for value, cls in [*((item, Assignment) for item in partition.assignments),
                       *((item, CandidateScore) for item in partition.candidate_scores)]:
        _record(value, cls)
        _safe_metadata(object.__getattribute__(value, "__dict__"))
    legacy._name(partition.graph_name)
    for assignment in partition.assignments:
        if (type(assignment.reason) is not str or
                assignment.reason.startswith(("fallback:", "manual_override:"))):
            raise ValueError("bounded Add fallback assignment rejected")
    return legacy._checked_partition(module, partition, targets)


def _primitives(specs: tuple[KernelSpec, ...]) -> tuple[str, str, str]:
    header = ["#ifndef TUC_BOUNDED_ADD_GENERATED_H", "#define TUC_BOUNDED_ADD_GENERATED_H",
              "/* Inert CPU primitives; caller validates extents, aliasing and numeric domain. */",
              "#ifdef __cplusplus", 'extern "C" {', "#endif"]
    source = ['#include "generated.h"', "#include <stddef.h>", "#include <float.h>",
              "#ifdef __FAST_MATH__", '#error "bounded Add forbids fast math"', "#endif",
              '_Static_assert(sizeof(float) == 4 && FLT_RADIX == 2 && FLT_MANT_DIG == 24,',
              '               "bounded Add requires binary32");',
              '_Static_assert(FLT_MAX_EXP == 128 && FLT_MIN_EXP == -125 && FLT_EVAL_METHOD == 0,',
              '               "bounded Add requires binary32 evaluation");',
              "/* -std=c11 -fno-fast-math -ffp-contract=off -frounding-math; FE_TONEAREST. */", ""]
    for spec in specs:
        declaration = f"void tuc_dag_op_{spec.index}({_parameters(spec)})"
        header.append(declaration + ";")
        if spec.kind in ("add", "add_row_bias"):
            rhs = "index" if spec.kind == "add" else f"index % {spec.output_shape[1]}U"
            body = [f"  for (size_t index = 0; index < {prod(spec.output_shape)}U; ++index) {{",
                    f"    volatile float value = input_0[index] + input_1[{rhs}];",
                    "    output[index] = value;", "  }"]
        else:
            body = _body(spec, False)
        source += [declaration + " {", *body, "}", ""]
    header += ["#ifdef __cplusplus", "}", "#endif", "#endif", ""]
    cuda = '#error "bounded Add DAG is CPU-only; no CUDA source is emitted"\n'
    return "\n".join(header), "\n".join(source), cuda


def _schedule(module: IRModule, plan: ResidencyPlan, specs: tuple[KernelSpec, ...],
              tensors: dict[str, int]) -> str:
    operations = {op.name: index for index, op in enumerate(module.graph.operations)}
    lines = ["#ifndef TUC_BOUNDED_ADD_SCHEDULE_H", "#define TUC_BOUNDED_ADD_SCHEDULE_H",
             "/* CPU-only static data; no allocation or dispatch authority. */",
             "enum tuc_add_op_kind { TUC_ADD_MATMUL=0, TUC_ADD_RELU=1, TUC_ADD_SUM_AXIS1=2,",
             "  TUC_ADD_EQUAL=3, TUC_ADD_ROW_BIAS=4 };",
             "struct tuc_add_buffer { unsigned int tensor, bytes; };",
             "struct tuc_add_operation { unsigned int kind, input0, input1, output; };",
             "struct tuc_add_event { unsigned int kind, operation, input0, input1, output; };",
             f"#define TUC_ADD_BUFFER_COUNT {len(plan.buffers)}U",
             f"#define TUC_ADD_OPERATION_COUNT {len(specs)}U",
             f"#define TUC_ADD_EVENT_COUNT {len(plan.steps)}U",
             "static const struct tuc_add_buffer tuc_add_buffers[] = {"]
    lines += [f"  {{{tensors[b.tensor]}U, {b.bytes}U}}," for b in plan.buffers]
    lines += ["};", "static const struct tuc_add_operation tuc_add_operations[] = {"]
    for op, spec in zip(module.graph.operations, specs, strict=True):
        second = tensors[op.inputs[1].name] if len(op.inputs) == 2 else 255
        lines.append(f"  {{{_KINDS[spec.kind]}U, {tensors[op.inputs[0].name]}U, "
                     f"{second}U, {tensors[op.outputs[0].name]}U}},")
    lines += ["};", "static const struct tuc_add_event tuc_add_events[] = {"]
    for step in plan.steps:
        inputs = (*step.inputs, 255, 255)
        output = step.outputs[0] if step.outputs else 255
        lines.append(f"  {{{_EVENTS[step.kind]}U, {operations.get(step.operation, 255)}U, "
                     f"{inputs[0]}U, {inputs[1]}U, {output}U}},")
    return "\n".join([*lines, "};", "#endif", ""])


def lower_bounded_add_dag(hac_ir: IRModule, partition: PartitionPlan,
                          targets: dict[str, DAGTarget]) -> BoundedDAGArtifacts:
    """Validate and emit one CPU-only graph containing explicit hardware-neutral Add."""
    specs, work = _checked_graph(hac_ir)
    spaces = _partition(hac_ir, partition, targets)
    plan = plan_residency(hac_ir.graph, partition, spaces,
                          ResidencySpace("host", MemoryDomainKind.HOST_RAM))
    if (len(plan.buffers) > legacy.MAX_DAG_BUFFERS or len(plan.steps) > legacy.MAX_DAG_EVENTS or
            sum(buffer.bytes for buffer in plan.buffers) > legacy.MAX_DAG_BUFFER_BYTES or
            plan.copy_bytes or any(b.space.name != "host" for b in plan.buffers) or
            any(step.kind == "copy" for step in plan.steps)):
        raise ValueError("bounded Add residency budget or CPU scope rejected")
    tensors = {t.name: t for op in hac_ir.graph.operations for t in (*op.inputs, *op.outputs)}
    ids = {name: index for index, name in enumerate(tensors)}
    op_ids = {op.name: index for index, op in enumerate(hac_ir.graph.operations)}
    terminal = tuple(plan.buffers[step.inputs[0]].tensor for step in plan.steps
                     if step.kind == "publish_output")
    public = legacy._public_outputs(hac_ir, terminal)
    hac_dump = dump_module(hac_ir)
    if len(hac_dump.encode("utf-8")) > legacy.MAX_DAG_METADATA_BYTES:
        raise ValueError("bounded Add HAC dump budget rejected")
    header, source, cuda = _primitives(specs)
    schedule = _schedule(hac_ir, plan, specs, ids)
    texts = {"generated.h": header, "generated.c": source,
             "kernels.cuh": cuda, "schedule.h": schedule}
    manifest = {
        "schema_version": SCHEMA_VERSION, "graph_name": hac_ir.graph.name,
        "hac_ir": hac_dump, "hac_ir_digest": legacy._digest(hac_dump),
        "targets": {name: target.value for name, target in targets.items()},
        "tensors": [{"index": ids[name], "name": name, "shape": list(t.shape),
                     "dtype": t.dtype, "bytes": prod(t.shape) * 4} for name, t in tensors.items()],
        "operations": [{"index": i, "name": op.name, "kind": spec.kind,
                        "inputs": [ids[t.name] for t in op.inputs],
                        "outputs": [ids[op.outputs[0].name]],
                        "input_shapes": [list(shape) for shape in spec.input_shapes],
                        "output_shape": list(spec.output_shape), "target": "c11",
                        "symbol": f"tuc_dag_op_{i}", "scalar_work": work[i]}
                       for i, (op, spec) in enumerate(zip(hac_ir.graph.operations, specs,
                                                        strict=True))],
        "buffers": [{"index": i, "tensor": ids[b.tensor], "space": "host", "bytes": b.bytes}
                    for i, b in enumerate(plan.buffers)],
        "events": [{"index": i, "kind": s.kind, "operation": op_ids.get(s.operation),
                    "target": "c11" if s.kind == "execute" else None,
                    "inputs": list(s.inputs), "outputs": list(s.outputs)}
                   for i, s in enumerate(plan.steps)],
        "input_tensors": [ids[plan.buffers[s.outputs[0]].tensor] for s in plan.steps
                          if s.kind == "bind_input"],
        "output_tensors": [ids[name] for name in terminal],
        "public_outputs": [{"public_name": name, "tensor": ids[tensor]}
                           for name, tensor in public.items()],
        "planned_buffer_bytes": sum(b.bytes for b in plan.buffers), "planned_copy_bytes": 0,
        "scalar_work": sum(work),
        "source_digests": {name: legacy._digest(text) for name, text in texts.items()},
        "numeric_policy": {
            "dtype": "float32", "rounding": "nearest_ties_even",
            "addition": "one_binary32_addition_per_element",
            "broadcast": "equal_shapes_or_rank2_lhs_with_rank1_rhs_row_bias_only",
            "matmul": "separate_binary32_product_and_sequential_inner_sum",
            "reduction": "sequential_axis1_sum", "fma_contraction": False,
            "reassociation": False, "error_budget_proven": False,
            "intermediate_domain": "finite_normal_or_zero_required_by_wrapper",
            "underflow_overflow": "not_validated_by_primitive_source_emission",
            "c11_flags": ["-std=c11", "-fno-fast-math", "-ffp-contract=off", "-frounding-math"],
            "wrapper_obligations": ["validate_live_disjoint_buffer_extents",
                                    "validate_readiness_and_all_numeric_intermediates",
                                    "FE_TONEAREST_FTZ_DAZ_off_masked_exceptions"],
        },
        "cuda_source_emitted": False, "native_execution_observed": False,
        "normal_runtime_admission": False, "latency_ns": None, "energy_pj": None,
        "blocked_claims": ["CUDA", "native_execution", "general_native_runtime", "performance",
                           "arbitrary_input_correctness", "error_budget_proof"],
    }
    artifacts = BoundedDAGArtifacts(legacy._json(manifest), header, source, cuda, schedule)
    legacy._check_artifact_budget(artifacts)
    return artifacts


def validate_bounded_add_dag_artifacts(artifacts: BoundedDAGArtifacts, hac_ir: IRModule,
                                      partition: PartitionPlan,
                                      targets: dict[str, DAGTarget]) -> None:
    """Compare exact bounded artifact fields against independently regenerated text."""
    _record(artifacts, BoundedDAGArtifacts)
    legacy._check_artifact_budget(artifacts)
    expected = lower_bounded_add_dag(hac_ir, partition, targets)
    for item in fields(BoundedDAGArtifacts):
        if getattr(artifacts, item.name) != getattr(expected, item.name):
            raise ValueError("bounded Add artifact differs from source")


__all__ = ["lower_bounded_add_dag", "validate_bounded_add_dag_artifacts"]
