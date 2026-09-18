"""Pure, bounded HAC-IR DAG lowering to reviewable C11 and CUDA artifacts.

This module produces source text and static schedule data. It never compiles,
loads, or executes an artifact and does not register a runtime backend.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields
from enum import StrEnum
from hashlib import sha256
from math import isfinite, prod
from types import MappingProxyType
from typing import cast

from tuc.backends.bounded_dag_codegen import KernelSpec, emit_kernels
from tuc.ir.dialect import validate_hac_module_contract
from tuc.ir.dump import dump_module
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.modules import IRModule, IRStage
from tuc.runtime.overrides import RuntimeOverrideEffect
from tuc.runtime.partitioning import Assignment, CandidateScore, PartitionPlan
from tuc.runtime.plan import RuntimeTransferEdge, TransferCostEstimate
from tuc.runtime.residency import ResidencyPlan, ResidencySpace, plan_residency

MAX_DAG_OPERATIONS = 8
MAX_DAG_TENSORS = 24
MAX_DAG_DIMENSION = 64
MAX_DAG_BUFFERS = 48
MAX_DAG_EVENTS = 96
MAX_DAG_BUFFER_BYTES = 256 * 1024
MAX_DAG_SCALAR_WORK = 1_000_000
MAX_DAG_ARTIFACT_BYTES = 256 * 1024
MAX_DAG_METADATA_BYTES = 64 * 1024
MAX_DAG_NAME_BYTES = 64

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_BACKEND_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*\Z")
_BOOLEAN_HINTS = frozenset({"robust_to_noise", "prefer_sparsity", "prefer_linear_accelerator"})
_EVENT_KIND = {"bind_input": 0, "copy": 1, "execute": 2, "publish_output": 3}
_OP_KIND = {"matmul": 0, "relu": 1, "sum_axis1": 2}
_NONE = 255


class DAGTarget(StrEnum):
    """Two explicit review-time source targets; neither grants execution."""

    C11 = "c11"
    CUDA_SM86 = "cuda-sm86"


@dataclass(frozen=True)
class BoundedDAGArtifacts:
    """Immutable source texts and their canonical, non-execution manifest."""

    manifest_json: str
    c11_header: str
    c11_source: str
    cuda_source: str
    schedule_header: str

    def files(self) -> dict[str, str]:
        """Return new in-memory file data; no filesystem operation is performed."""
        return {
            "manifest.json": self.manifest_json,
            "generated.h": self.c11_header,
            "generated.c": self.c11_source,
            "kernels.cuh": self.cuda_source,
            "schedule.h": self.schedule_header,
        }


def _name(value: object, *, backend: bool = False) -> str:
    pattern = _BACKEND_NAME if backend else _NAME
    if (
        type(value) is not str
        or len(value) > MAX_DAG_NAME_BYTES
        or len(value.encode("utf-8")) > MAX_DAG_NAME_BYTES
        or pattern.fullmatch(value) is None
    ):
        raise ValueError("bounded DAG name rejected")
    return value


def _metadata(value: object) -> object:
    """Check exact data types and budgets before dumping caller metadata."""
    remaining = 4096
    text_bytes = 0

    def visit(item: object, depth: int) -> object:
        nonlocal remaining, text_bytes
        remaining -= 1
        if remaining < 0 or depth > 8:
            raise ValueError("bounded DAG metadata structure rejected")
        if item is None or type(item) is bool:
            return item
        if type(item) is int:
            if item.bit_length() > 63:
                raise ValueError("bounded DAG metadata integer rejected")
            return item
        if type(item) is float:
            if not isfinite(item):
                raise ValueError("bounded DAG metadata number rejected")
            return item
        if type(item) in (LayoutKind, MemoryDomainKind):
            return visit(cast(StrEnum, item).value, depth)
        if type(item) is str:
            if len(item) > 4096:
                raise ValueError("bounded DAG metadata text rejected")
            size = len(item.encode("utf-8"))
            text_bytes += size
            if size > 4096 or text_bytes > MAX_DAG_METADATA_BYTES:
                raise ValueError("bounded DAG metadata text rejected")
            return item
        if type(item) is tuple:
            if len(item) > 128:
                raise ValueError("bounded DAG metadata sequence rejected")
            return [visit(child, depth + 1) for child in item]
        if type(item) in (dict, MappingProxyType):
            mapping = cast(dict[object, object], item)
            if len(mapping) > 128 or any(type(key) is not str for key in mapping):
                raise ValueError("bounded DAG metadata mapping rejected")
            return {
                cast(str, visit(key, depth + 1)): visit(child, depth + 1)
                for key, child in mapping.items()
            }
        raise ValueError("bounded DAG metadata type rejected")

    normalized = visit(value, 0)
    if len(_json(normalized).encode("utf-8")) > MAX_DAG_METADATA_BYTES:
        raise ValueError("bounded DAG metadata byte budget exceeded")
    return normalized


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(text: str) -> str:
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


def _tensor(value: TensorRef) -> None:
    if type(value) is not TensorRef:
        raise ValueError("bounded DAG tensor type rejected")
    _name(value.name)
    if (
        type(value.dtype) is not str
        or value.dtype != "float32"
        or type(value.shape) is not tuple
        or not 1 <= len(value.shape) <= 2
        or any(type(d) is not int or not 1 <= d <= MAX_DAG_DIMENSION for d in value.shape)
    ):
        raise ValueError("bounded DAG tensor shape or dtype rejected")


def _operation(value: ComputeOperation, index: int) -> tuple[KernelSpec, int]:
    if (
        type(value) is not ComputeOperation
        or type(value.kind) is not OperationKind
        or type(value.inputs) is not tuple
        or type(value.outputs) is not tuple
        or not 1 <= len(value.inputs) <= 2
        or len(value.outputs) != 1
        or type(value.attributes) is not MappingProxyType
    ):
        raise ValueError("bounded DAG operation type or arity rejected")
    _name(value.name)
    for tensor in (*value.inputs, *value.outputs):
        _tensor(tensor)
    _metadata(value.attributes)
    semantics = {key for key in value.attributes if not key.startswith("tuc.")}
    # These frontend hints affect planning only, never the generated arithmetic.
    for key in _BOOLEAN_HINTS.intersection(semantics):
        if type(value.attributes[key]) is not bool:
            raise ValueError("bounded DAG boolean hint rejected")
    semantics -= _BOOLEAN_HINTS
    if "max_error_budget" in semantics:
        budget = value.attributes["max_error_budget"]
        if type(budget) not in (int, float) or cast(float, budget) < 0:
            raise ValueError("bounded DAG error hint rejected")
        semantics.remove("max_error_budget")
    layout = value.attributes.get("tuc.layout")
    tile = value.attributes.get("tuc.layout_tile_shape")
    if (
        type(layout) not in (str, LayoutKind)
        or layout != LayoutKind.ROW_MAJOR
        or type(tile) is not tuple
        or tile
    ):
        raise ValueError("bounded DAG requires row-major layout")
    shapes = tuple(tensor.shape for tensor in value.inputs)
    output = value.outputs[0].shape
    if value.kind is OperationKind.MATMUL:
        if semantics or len(shapes) != 2 or any(len(shape) != 2 for shape in (*shapes, output)):
            raise ValueError("bounded DAG matmul semantics rejected")
        rows, inner = shapes[0]
        other_inner, columns = shapes[1]
        if inner != other_inner or output != (rows, columns):
            raise ValueError("bounded DAG matmul shape rejected")
        kind, work = "matmul", 2 * rows * inner * columns
    elif value.kind is OperationKind.ELEMENTWISE:
        if (
            semantics != {"kernel"}
            or type(value.attributes["kernel"]) is not str
            or value.attributes["kernel"] != "relu"
            or len(shapes) != 1
            or output != shapes[0]
        ):
            raise ValueError("bounded DAG ReLU semantics rejected")
        kind, work = "relu", prod(output)
    elif value.kind is OperationKind.REDUCTION:
        if (
            semantics != {"axis"}
            or type(value.attributes["axis"]) is not int
            or value.attributes["axis"] != 1
            or len(shapes) != 1
            or len(shapes[0]) != 2
            or output != (shapes[0][0],)
        ):
            raise ValueError("bounded DAG Sum semantics rejected")
        kind, work = "sum_axis1", prod(shapes[0])
    else:
        raise ValueError("bounded DAG operation kind unsupported")
    return KernelSpec(index, kind, shapes, output), work


def _checked_graph(module: IRModule) -> tuple[tuple[KernelSpec, ...], tuple[int, ...]]:
    if (
        type(module) is not IRModule
        or type(module.stage) is not IRStage
        or module.stage is not IRStage.HAC_IR
        or module.target is not None
        or type(module.graph) is not ComputeGraph
        or type(module.metadata) is not dict
        or type(module.graph.metadata) is not MappingProxyType
        or type(module.graph.operations) is not tuple
        or not 1 <= len(module.graph.operations) <= MAX_DAG_OPERATIONS
    ):
        raise ValueError("bounded DAG HAC-IR boundary rejected")
    _name(module.graph.name)
    _metadata(module.metadata)
    _metadata(module.graph.metadata)
    specs, work = [], []
    tensors: dict[str, TensorRef] = {}
    operations: set[str] = set()
    for index, operation in enumerate(module.graph.operations):
        spec, amount = _operation(operation, index)
        if operation.name in operations:
            raise ValueError("bounded DAG duplicate operation rejected")
        operations.add(operation.name)
        for tensor in (*operation.inputs, *operation.outputs):
            if tensor.name in tensors and tensors[tensor.name] != tensor:
                raise ValueError("bounded DAG tensor identity mismatch")
            tensors[tensor.name] = tensor
        specs.append(spec)
        work.append(amount)
    if len(tensors) > MAX_DAG_TENSORS or sum(work) > MAX_DAG_SCALAR_WORK:
        raise ValueError("bounded DAG tensor or scalar-work budget exceeded")
    _metadata(
        (
            module.metadata,
            module.graph.metadata,
            tuple(operation.attributes for operation in module.graph.operations),
        )
    )
    validate_hac_module_contract(module)
    return tuple(specs), tuple(work)


def _checked_partition(
    module: IRModule, partition: PartitionPlan, targets: dict[str, DAGTarget]
) -> dict[str, ResidencySpace]:
    if (
        type(partition) is not PartitionPlan
        or type(partition.assignments) is not tuple
        or len(partition.assignments) != len(module.graph.operations)
        or type(partition.transfer_edges) is not tuple
        or len(partition.transfer_edges) > MAX_DAG_OPERATIONS * 2
        or type(partition.layout_conversions) is not tuple
        or partition.layout_conversions
        or type(targets) is not dict
        or not 1 <= len(targets) <= 2
    ):
        raise ValueError("bounded DAG partition or target boundary rejected")
    if _name(partition.graph_name) != module.graph.name:
        raise ValueError("bounded DAG partition graph mismatch")
    spaces = {}
    for name, target in targets.items():
        _name(name, backend=True)
        if type(target) is not DAGTarget:
            raise ValueError("bounded DAG target rejected")
        spaces[name] = (
            ResidencySpace("host", MemoryDomainKind.HOST_RAM)
            if target is DAGTarget.C11
            else ResidencySpace("accelerator", MemoryDomainKind.UNKNOWN)
        )
    if len(set(targets.values())) != len(targets):
        raise ValueError("bounded DAG target aliases rejected")
    used = set()
    for operation, assignment in zip(module.graph.operations, partition.assignments, strict=True):
        if type(assignment) is not Assignment:
            raise ValueError("bounded DAG assignment type rejected")
        _name(assignment.operation_name)
        _name(assignment.backend_name, backend=True)
        if (
            assignment.operation_name != operation.name
            or assignment.backend_name not in spaces
            or type(assignment.memory_domain) is not MemoryDomainKind
            or assignment.memory_domain != spaces[assignment.backend_name].physical_kind
            or type(assignment.produced_layout) is not LayoutKind
            or assignment.produced_layout is not LayoutKind.ROW_MAJOR
            or type(assignment.reason) is not str
            or not 0 < len(assignment.reason) <= 4096
            or type(assignment.transfer_bytes) is not int
            or not 0 <= assignment.transfer_bytes <= MAX_DAG_BUFFER_BYTES
            or type(assignment.layout_conversion_bytes) is not int
            or assignment.layout_conversion_bytes != 0
        ):
            raise ValueError("bounded DAG assignment rejected")
        used.add(assignment.backend_name)
    if used != set(targets):
        raise ValueError("bounded DAG target coverage rejected")
    for edge in partition.transfer_edges:
        if type(edge) is not RuntimeTransferEdge:
            raise ValueError("bounded DAG transfer type rejected")
        for name in (edge.tensor_name, edge.source_operation, edge.target_operation):
            _name(name)
        for name in (edge.source_backend, edge.target_backend):
            _name(name, backend=True)
        if (
            type(edge.bytes_moved) is not int
            or not 0 < edge.bytes_moved <= MAX_DAG_BUFFER_BYTES
            or type(edge.source_domain) is not MemoryDomainKind
            or type(edge.target_domain) is not MemoryDomainKind
            or type(edge.source_layout) is not LayoutKind
            or type(edge.target_layout) is not LayoutKind
            or edge.source_layout is not LayoutKind.ROW_MAJOR
            or edge.target_layout is not LayoutKind.ROW_MAJOR
            or type(edge.cost_estimate) is not TransferCostEstimate
            or type(edge.cost_estimate.bytes_moved) is not int
            or edge.cost_estimate.bytes_moved != edge.bytes_moved
        ):
            raise ValueError("bounded DAG transfer contract rejected")
        _metadata(
            {
                field.name: getattr(edge.cost_estimate, field.name)
                for field in fields(TransferCostEstimate)
            }
        )
        for field_name, positive in (
            ("bandwidth_gb_s", True),
            ("base_latency_ns", False),
            ("energy_pj_per_byte", False),
        ):
            number = getattr(edge.cost_estimate, field_name)
            if (
                type(number) not in (int, float)
                or not isfinite(number)
                or (number <= 0 if positive else number < 0)
            ):
                raise ValueError("bounded DAG transfer cost rejected")
    for assignment in partition.assignments:
        if assignment.transfer_bytes != sum(
            edge.bytes_moved
            for edge in partition.transfer_edges
            if edge.target_operation == assignment.operation_name
        ):
            raise ValueError("bounded DAG assignment transfer accounting rejected")
    # Diagnostic facts do not influence emission, but cannot carry arbitrary objects.
    for values, expected in (
        (partition.override_effects, RuntimeOverrideEffect),
        (partition.candidate_scores, CandidateScore),
    ):
        if type(values) is not tuple or len(values) > 64:
            raise ValueError("bounded DAG partition diagnostic budget rejected")
        for value in values:
            if type(value) is not expected:
                raise ValueError("bounded DAG partition diagnostic type rejected")
            _metadata({field.name: getattr(value, field.name) for field in fields(expected)})
    return spaces


def _public_outputs(module: IRModule, terminal_names: tuple[str, ...]) -> dict[str, str]:
    policy_key = "frontend.source_intent_return_policy"
    aliases_key = "frontend.source_intent_return_aliases"
    metadata = module.graph.metadata
    if policy_key not in metadata and aliases_key not in metadata:
        return {name: name for name in terminal_names}
    aliases = metadata.get(aliases_key)
    if (
        type(metadata.get(policy_key)) is not str
        or metadata[policy_key] != "explicit_public_returns"
        or type(aliases) is not tuple
        or not 0 < len(aliases) <= MAX_DAG_TENSORS
    ):
        raise ValueError("bounded DAG public return contract rejected")
    result: dict[str, str] = {}
    returned: set[str] = set()
    for alias in aliases:
        if type(alias) is not str or alias.count(":") != 1:
            raise ValueError("bounded DAG public return alias rejected")
        public, tensor = alias.split(":")
        _name(public)
        _name(tensor)
        if public in result or tensor in returned:
            raise ValueError("bounded DAG duplicate public return rejected")
        result[public] = tensor
        returned.add(tensor)
    if returned != set(terminal_names):
        raise ValueError("bounded DAG requires exact terminal public returns")
    return result


def _schedule_header(
    module: IRModule,
    plan: ResidencyPlan,
    specs: tuple[KernelSpec, ...],
    tensor_ids: dict[str, int],
    targets: dict[str, DAGTarget],
) -> str:
    op_ids = {op.name: index for index, op in enumerate(module.graph.operations)}
    lines = [
        "#ifndef TUC_BOUNDED_DAG_SCHEDULE_H",
        "#define TUC_BOUNDED_DAG_SCHEDULE_H",
        "/* Static data only: no allocation, dispatch, or execution admission. */",
        "enum tuc_dag_event_kind { TUC_DAG_BIND = 0, TUC_DAG_COPY = 1,",
        "  TUC_DAG_EXECUTE = 2, TUC_DAG_PUBLISH = 3 };",
        "enum tuc_dag_target { TUC_DAG_C11 = 0, TUC_DAG_CUDA_SM86 = 1, TUC_DAG_NONE = 255 };",
        "enum tuc_dag_op_kind { TUC_DAG_MATMUL = 0, TUC_DAG_RELU = 1, TUC_DAG_SUM_AXIS1 = 2 };",
        "struct tuc_dag_buffer { unsigned int tensor, space, bytes; };",
        "struct tuc_dag_operation { unsigned int kind, input0, input1, output; };",
        "struct tuc_dag_event { unsigned int kind, operation, target, input0, input1, output; };",
        f"#define TUC_DAG_BUFFER_COUNT {len(plan.buffers)}U",
        f"#define TUC_DAG_OPERATION_COUNT {len(specs)}U",
        f"#define TUC_DAG_EVENT_COUNT {len(plan.steps)}U",
        "static const struct tuc_dag_buffer tuc_dag_buffers[] = {",
    ]
    for buffer in plan.buffers:
        lines.append(
            f"  {{{tensor_ids[buffer.tensor]}U, {int(buffer.space.name == 'accelerator')}U, "
            f"{buffer.bytes}U}},"
        )
    lines.extend(["};", "static const struct tuc_dag_operation tuc_dag_operations[] = {"])
    for op, spec in zip(module.graph.operations, specs, strict=True):
        operation_inputs = [tensor_ids[t.name] for t in op.inputs]
        second = operation_inputs[1] if len(operation_inputs) == 2 else _NONE
        lines.append(
            f"  {{{_OP_KIND[spec.kind]}U, {operation_inputs[0]}U, {second}U, "
            f"{tensor_ids[op.outputs[0].name]}U}},"
        )
    lines.extend(["};", "static const struct tuc_dag_event tuc_dag_events[] = {"])
    for step in plan.steps:
        event_inputs = (*step.inputs, _NONE, _NONE)
        output = step.outputs[0] if step.outputs else _NONE
        target = (
            int(targets[step.backend] is DAGTarget.CUDA_SM86) if step.kind == "execute" else _NONE
        )
        lines.append(
            f"  {{{_EVENT_KIND[step.kind]}U, {op_ids.get(step.operation, _NONE)}U, "
            f"{target}U, {event_inputs[0]}U, {event_inputs[1]}U, {output}U}},"
        )
    return "\n".join([*lines, "};", "#endif", ""])


def _check_artifact_budget(artifacts: BoundedDAGArtifacts) -> None:
    if type(artifacts) is not BoundedDAGArtifacts:
        raise ValueError("bounded DAG artifact type rejected")
    total = 0
    for field in fields(BoundedDAGArtifacts):
        value = getattr(artifacts, field.name)
        if type(value) is not str or not value or len(value) > MAX_DAG_ARTIFACT_BYTES:
            raise ValueError("bounded DAG artifact field rejected")
        total += len(value.encode("utf-8"))
        if total > MAX_DAG_ARTIFACT_BYTES:
            raise ValueError("bounded DAG artifact byte budget exceeded")


def lower_bounded_dag(
    hac_ir: IRModule,
    partition: PartitionPlan,
    targets: dict[str, DAGTarget],
) -> BoundedDAGArtifacts:
    """Validate a bounded DAG, derive residency, and emit source without execution."""
    specs, work = _checked_graph(hac_ir)
    spaces = _checked_partition(hac_ir, partition, targets)
    plan = plan_residency(
        hac_ir.graph, partition, spaces, ResidencySpace("host", MemoryDomainKind.HOST_RAM)
    )
    if (
        len(plan.buffers) > MAX_DAG_BUFFERS
        or len(plan.steps) > MAX_DAG_EVENTS
        or sum(buffer.bytes for buffer in plan.buffers) > MAX_DAG_BUFFER_BYTES
    ):
        raise ValueError("bounded DAG residency budget exceeded")
    tensors = {
        tensor.name: tensor
        for op in hac_ir.graph.operations
        for tensor in (*op.inputs, *op.outputs)
    }
    tensor_ids = {name: index for index, name in enumerate(tensors)}
    op_ids = {op.name: index for index, op in enumerate(hac_ir.graph.operations)}
    terminal_names = tuple(
        plan.buffers[step.inputs[0]].tensor for step in plan.steps if step.kind == "publish_output"
    )
    public_outputs = _public_outputs(hac_ir, terminal_names)
    hac_dump = dump_module(hac_ir)
    if len(hac_dump.encode("utf-8")) > MAX_DAG_METADATA_BYTES:
        raise ValueError("bounded DAG HAC dump budget exceeded")
    header, source, cuda = emit_kernels(specs)
    schedule = _schedule_header(hac_ir, plan, specs, tensor_ids, targets)
    texts = {
        "generated.h": header,
        "generated.c": source,
        "kernels.cuh": cuda,
        "schedule.h": schedule,
    }
    manifest = {
        "schema_version": "tuc.bounded_dag_artifacts.v0",
        "graph_name": hac_ir.graph.name,
        "hac_ir": hac_dump,
        "hac_ir_digest": _digest(hac_dump),
        "targets": {name: target.value for name, target in targets.items()},
        "tensors": [
            {
                "index": tensor_ids[name],
                "name": name,
                "shape": list(tensor.shape),
                "dtype": tensor.dtype,
                "bytes": prod(tensor.shape) * 4,
            }
            for name, tensor in tensors.items()
        ],
        "operations": [
            {
                "index": index,
                "name": op.name,
                "kind": spec.kind,
                "inputs": [tensor_ids[t.name] for t in op.inputs],
                "outputs": [tensor_ids[t.name] for t in op.outputs],
                "input_shapes": [list(shape) for shape in spec.input_shapes],
                "output_shape": list(spec.output_shape),
                "target": targets[assignment.backend_name].value,
                "symbol": f"tuc_dag_op_{index}",
                "cuda_symbol": f"tuc_dag_cuda_op_{index}",
                "launch": {
                    "blocks": (prod(spec.output_shape) + 127) // 128,
                    "threads_per_block": 128,
                    "dimensions": 1,
                },
                "scalar_work": work[index],
            }
            for index, (op, spec, assignment) in enumerate(
                zip(hac_ir.graph.operations, specs, partition.assignments, strict=True)
            )
        ],
        "buffers": [
            {
                "index": index,
                "tensor": tensor_ids[buffer.tensor],
                "space": buffer.space.name,
                "bytes": buffer.bytes,
            }
            for index, buffer in enumerate(plan.buffers)
        ],
        "events": [
            {
                "index": index,
                "kind": step.kind,
                "operation": op_ids.get(step.operation),
                "target": targets[step.backend].value if step.kind == "execute" else None,
                "inputs": list(step.inputs),
                "outputs": list(step.outputs),
            }
            for index, step in enumerate(plan.steps)
        ],
        "input_tensors": [
            tensor_ids[plan.buffers[step.outputs[0]].tensor]
            for step in plan.steps
            if step.kind == "bind_input"
        ],
        "output_tensors": [
            tensor_ids[plan.buffers[step.inputs[0]].tensor]
            for step in plan.steps
            if step.kind == "publish_output"
        ],
        "public_outputs": [
            {"public_name": name, "tensor": tensor_ids[tensor]}
            for name, tensor in public_outputs.items()
        ],
        "planned_buffer_bytes": sum(buffer.bytes for buffer in plan.buffers),
        "planned_copy_bytes": plan.copy_bytes,
        "scalar_work": sum(work),
        "source_digests": {name: _digest(value) for name, value in texts.items()},
        "numeric_policy": {
            "dtype": "float32",
            "rounding": "nearest_ties_even",
            "matmul": "separate_binary32_product_and_sequential_inner_sum",
            "reduction": "sequential_axis1_sum",
            "fma_contraction": False,
            "reassociation": False,
            "signed_zero": "numerical_equality_only",
            "error_budget_proven": False,
            "finite_inputs_required": True,
            "intermediate_domain": "finite_normal_or_zero_required_by_wrapper",
            "underflow_overflow": "not_validated_by_source_emission",
            "c11_flags": ["-std=c11", "-fno-fast-math", "-ffp-contract=off"],
            "c11_rounding_environment": "FE_TONEAREST",
            "c11_denormal_environment": "FTZ_and_DAZ_disabled",
            "cuda_flags": ["--ftz=false", "--fmad=false", "-gencode", "arch=compute_86,code=sm_86"],
            "wrapper_obligations": [
                "validate_allocated_buffer_extents",
                "nonoverlapping_output_and_inputs",
                "validate_slot_readiness",
                "validate_finite_normal_or_zero_intermediates",
                "validate_rounding_and_no_flush_environment",
                "exact_1d_cuda_launch",
            ],
        },
        "native_execution_observed": False,
        "normal_runtime_admission": False,
        "latency_ns": None,
        "energy_pj": None,
        "blocked_claims": [
            "native_execution",
            "general_native_runtime",
            "arbitrary_input_correctness",
            "error_budget_proof",
            "performance",
            "independent_reproduction",
            "concurrent_execution",
        ],
    }
    artifacts = BoundedDAGArtifacts(_json(manifest), header, source, cuda, schedule)
    _check_artifact_budget(artifacts)
    return artifacts


def validate_bounded_dag_artifacts(
    artifacts: BoundedDAGArtifacts,
    hac_ir: IRModule,
    partition: PartitionPlan,
    targets: dict[str, DAGTarget],
) -> None:
    """Reject artifact drift by bounded exact-type checks and full re-emission."""
    _check_artifact_budget(artifacts)
    if artifacts != lower_bounded_dag(hac_ir, partition, targets):
        raise ValueError("bounded DAG artifact binding rejected")
