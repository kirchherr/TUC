"""Pure source, residency and numeric candidate for a future bounded native fan-in."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from fractions import Fraction
from math import prod

from examples import bounded_composed_chain as chain
from examples import reduction_fp32_contract as fp
from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    _canonical_json,
    _digest_payload,
    _digest_text,
)
from examples.bounded_plan_native_bridge import _bounded_metadata
from examples.bounded_reduction_c11 import ROOT, _read_bounded_file
from tuc.backends.base import BackendCapability
from tuc.compiler import compile_graph
from tuc.frontend import (
    ingest_triton_module_source_to_source_intent,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.ir.modules import IRStage
from tuc.runtime.overrides import RuntimeOverrideAction, RuntimeOverrideRule, RuntimeOverrideSet
from tuc.runtime.residency import (
    ResidencyBuffer,
    ResidencyPlan,
    ResidencySpace,
    ResidencyStep,
    plan_residency,
)

CONTEXT = ROOT / "tests/golden/native_fanin_candidate"
PROFILES = ("cccc", "gccc", "cgcc", "gcgg", "cggg", "gggg")
SOURCE = """import triton
import triton.language as tl

@triton.jit
def relu_fanin(a, b, y):
    left = tl.where(a > 0, a, 0)
    right = tl.where(b > 0, b, 0)
    projection = tl.dot(left, right)
    row_sum = tl.sum(projection, axis=1)
    tl.store(y, row_sum)
"""
INTENT_DIGEST = "sha256:648dbbc6aeced9b09fd0e91a35aa9d4960368c45d5a652d2ad2d192170882131"
CONTRACT = {
    **fp.CONTRACT,
    "schema_version": "tuc.fanin_candidate_numeric_contract.v0",
    "reference": "sum_k_c(max(a[row,k],0)*max(b[k,c],0))_over_exact_binary32_inputs",
    "operation_order": ["relu_left", "relu_right", "sequential_matmul", "sequential_sum_axis1"],
    "absolute_error_bound": "gamma_13 * sum_k_c(max(a[row,k],0)*max(b[k,c],0))",
    "producer_rounding": "relu_is_exact_for_finite_binary32_inputs",
    "admission": "no_native_admission_candidate_only",
}
BLOCKED_CLAIMS = [
    "native_execution",
    "general_native_runtime",
    "arbitrary_inputs",
    "dynamic_shapes",
    "performance",
    "energy",
    "optimal_placement",
    "independent_reproduction",
]


def parse_source():
    return ingest_triton_module_source_to_source_intent(
        SOURCE,
        source_name="research_native_fanin_candidate",
        kernel_name="relu_fanin",
        tensor_shapes={"a": (33, 7), "b": (7, 5), "y": (33,)},
    ).parser_result.source_intent_payload


def checked_intent(payload):
    _bounded_metadata(payload)
    if _digest_payload(payload) != INTENT_DIGEST:
        raise BoundedCompilerEmissionError("fan-in Source Intent rejected")
    module = source_intent_from_mapping(payload)
    left, right, join, reduction = module.operations
    if (
        tuple(op.family for op in module.operations)
        != ("elementwise", "elementwise", "matmul", "reduction")
        or left.inputs != ("a",)
        or right.inputs != ("b",)
        or dict(left.attributes) != {"elementwise_kind": "relu"}
        or dict(right.attributes) != {"elementwise_kind": "relu"}
        or join.inputs != (*left.outputs, *right.outputs)
        or reduction.inputs != join.outputs
        or dict(reduction.attributes) != {"axis": 1}
        or any(t.dtype != "float32" for t in module.tensors)
    ):
        raise BoundedCompilerEmissionError("fan-in typed semantics rejected")
    return module


def compile_case(profile):
    if type(profile) is not str or profile not in PROFILES:
        raise BoundedCompilerEmissionError("fan-in profile rejected")
    graph = source_intent_to_triton_metadata(checked_intent(parse_source())).to_compute_graph()
    supported = frozenset(
        {OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}
    )
    host = ResidencySpace("host", MemoryDomainKind.HOST_RAM)
    spaces = {
        "bounded-c11": host,
        "bounded-cuda": ResidencySpace("accelerator", MemoryDomainKind.UNKNOWN),
    }
    caps = [
        BackendCapability(n, supported, memory_domain=s.physical_kind) for n, s in spaces.items()
    ]
    overrides = RuntimeOverrideSet(
        tuple(
            RuntimeOverrideRule(
                op.name,
                RuntimeOverrideAction.REQUIRE_BACKEND,
                "bounded-c11" if p == "c" else "bounded-cuda",
            )
            for op, p in zip(graph.operations, profile, strict=True)
        )
    )
    compiled = compile_graph(graph, caps, runtime_overrides=overrides)
    used = {a.backend_name: spaces[a.backend_name] for a in compiled.partition_plan.assignments}
    plan = plan_residency(compiled.hac_ir.graph, compiled.partition_plan, used, host)
    return compiled, plan


def inspect_schedule(compiled, plan):
    """Replay metadata readiness only; no tensors, allocations, calls or copies."""
    ops = compiled.hac_ir.graph.operations
    assignments = compiled.partition_plan.assignments
    if (
        type(plan) is not ResidencyPlan
        or plan.graph_name != compiled.hac_ir.graph.name
        or type(plan.buffers) is not tuple
        or not 6 <= len(plan.buffers) <= 9
        or type(plan.steps) is not tuple
        or not 7 <= len(plan.steps) <= 10
    ):
        raise BoundedCompilerEmissionError("fan-in schedule scope or budget rejected")
    tensors = {t.name: t for op in ops for t in (*op.inputs, *op.outputs)}
    spaces = (
        ResidencySpace("host", MemoryDomainKind.HOST_RAM),
        ResidencySpace("accelerator", MemoryDomainKind.UNKNOWN),
    )
    for buffer in plan.buffers:
        if (
            type(buffer) is not ResidencyBuffer
            or type(buffer.tensor) is not str
            or buffer.tensor not in tensors
            or type(buffer.space) is not ResidencySpace
            or buffer.space not in spaces
        ):
            raise BoundedCompilerEmissionError("fan-in buffer rejected")
        tensor = tensors[buffer.tensor]
        if (
            type(buffer.shape) is not tuple
            or any(type(d) is not int for d in buffer.shape)
            or buffer.shape != tensor.shape
            or buffer.dtype != tensor.dtype
            or type(buffer.bytes) is not int
            or buffer.bytes != prod(tensor.shape) * 4
        ):
            raise BoundedCompilerEmissionError("fan-in buffer contract rejected")
    ready, bound, published = set(), set(), set()
    executed, join = [], None
    for index, step in enumerate(plan.steps):
        if (
            type(step) is not ResidencyStep
            or type(step.inputs) is not tuple
            or type(step.outputs) is not tuple
            or len(step.inputs) > 2
            or len(step.outputs) > 1
            or (step.kind != "execute" and (step.operation or step.backend))
        ):
            raise BoundedCompilerEmissionError("fan-in event contract rejected")
        for slot in (*step.inputs, *step.outputs):
            if type(slot) is not int or not 0 <= slot < len(plan.buffers):
                raise BoundedCompilerEmissionError("fan-in slot rejected")
        inputs = tuple(plan.buffers[s] for s in step.inputs)
        outputs = tuple(plan.buffers[s] for s in step.outputs)
        if any(s not in ready for s in step.inputs) or any(s in ready for s in step.outputs):
            raise BoundedCompilerEmissionError("fan-in input unavailable or output reused")
        if step.kind == "bind_input":
            if (
                inputs
                or len(outputs) != 1
                or outputs[0].tensor not in ("a", "b")
                or outputs[0].tensor in bound
                or outputs[0].space.name != "host"
            ):
                raise BoundedCompilerEmissionError("fan-in input binding rejected")
            bound.add(outputs[0].tensor)
        elif step.kind == "copy":
            if (
                len(inputs) != 1
                or len(outputs) != 1
                or inputs[0].tensor != outputs[0].tensor
                or inputs[0].shape != outputs[0].shape
                or inputs[0].dtype != outputs[0].dtype
                or inputs[0].bytes != outputs[0].bytes
                or inputs[0].space == outputs[0].space
            ):
                raise BoundedCompilerEmissionError("fan-in copy rejected")
        elif step.kind == "execute":
            if len(executed) >= len(ops):
                raise BoundedCompilerEmissionError("fan-in extra operation rejected")
            op, assignment = ops[len(executed)], assignments[len(executed)]
            space = "host" if assignment.backend_name == "bounded-c11" else "accelerator"
            if (
                step.operation != op.name
                or step.backend != assignment.backend_name
                or tuple(b.tensor for b in inputs) != tuple(t.name for t in op.inputs)
                or tuple(b.tensor for b in outputs) != tuple(t.name for t in op.outputs)
                or any(b.space.name != space for b in (*inputs, *outputs))
            ):
                raise BoundedCompilerEmissionError("fan-in operation ports or placement rejected")
            if op.kind is OperationKind.MATMUL:
                join = {
                    "operation": op.name,
                    "step_index": index,
                    "space": space,
                    "operand_slots": list(step.inputs),
                    "operands": [b.tensor for b in inputs],
                    "producer_operations": [ops[0].name, ops[1].name],
                    "both_inputs_available_in_plan": True,
                }
            executed.append(op.name)
        elif step.kind == "publish_output":
            if (
                len(inputs) != 1
                or outputs
                or inputs[0].tensor != "row_sum"
                or inputs[0].space.name != "host"
                or published
            ):
                raise BoundedCompilerEmissionError("fan-in publication rejected")
            published.add(inputs[0].tensor)
        else:
            raise BoundedCompilerEmissionError("fan-in event rejected")
        ready.update(step.outputs)
    if (
        bound != {"a", "b"}
        or len(executed) != 4
        or published != {"row_sum"}
        or join is None
        or ready != set(range(len(plan.buffers)))
    ):
        raise BoundedCompilerEmissionError("fan-in schedule incomplete")
    return join


def snapshot(profile):
    compiled, plan = compile_case(profile)
    return {
        "schema_version": "tuc.fanin_candidate_plan.v0",
        "profile": profile,
        "source_intent_digest": INTENT_DIGEST,
        "hac_ir": compiled.dump(IRStage.HAC_IR),
        "hs_ir": compiled.dump(IRStage.HS_IR),
        "partition": compiled.dump_runtime_plan(),
        "decisions": compiled.dump_decision_report(),
        "overrides": json.loads(
            json.dumps([asdict(e) for e in compiled.partition_plan.override_effects])
        ),
        "residency": json.loads(json.dumps(asdict(plan))),
        "join": inspect_schedule(compiled, plan),
        "planned_copy_bytes": plan.copy_bytes,
        "planned_buffer_bytes": sum(b.bytes for b in plan.buffers),
        "native_execution_observed": False,
        "normal_runtime_admission": False,
        "latency_ns": None,
        "energy_pj": None,
    }


def validate_snapshot(value, profile):
    _bounded_metadata(value)
    if _canonical_json(value) != _canonical_json(snapshot(profile)):
        raise BoundedCompilerEmissionError("fan-in candidate plan rejected")


def corpus():
    cases = fp.corpus()
    dual = cases.pop(2)
    dual["name"] = "dual_signed"
    dual["b"] = [
        [x * (-1) ** (k + c) for c, x in enumerate(row)] for k, row in enumerate(dual["b"])
    ]
    return [dual, *cases]


def relu_inputs(case):
    _bounded_metadata(case)
    if (
        type(case) is not dict
        or set(case) != {"name", "a", "b"}
        or type(case["name"]) is not str
        or not 0 < len(case["name"]) <= 64
    ):
        raise BoundedCompilerEmissionError("fan-in numeric case rejected")
    fp.reference(case["a"], case["b"])
    return {key: [[max(x, 0.0) for x in row] for row in case[key]] for key in ("a", "b")}


def reference(case):
    positive = relu_inputs(case)
    return fp.reference(positive["a"], positive["b"])


def ordered_reference(case):
    return fp.ordered_reference(relu_inputs(case))


def numeric_summary():
    cases = corpus()
    refs = [reference(c) for c in cases]
    ordered = [ordered_reference(c) for c in cases]
    rounded = 0
    for i in (*range(10), 0):
        for value, (exact, budget) in zip(ordered[i], refs[i], strict=True):
            if abs(Fraction(value) - exact) > budget:
                raise BoundedCompilerEmissionError("fan-in corpus exceeds contract")
            rounded += value != float(exact)
    # Both signed operands make each omitted/misplaced producer observable on run one.
    first, positive = cases[0], relu_inputs(cases[0])
    wrong = {
        "bypass-left": fp.ordered_reference({"a": first["a"], "b": positive["b"]}),
        "bypass-right": fp.ordered_reference({"a": positive["a"], "b": first["b"]}),
        "bypass-both": fp.ordered_reference(first),
        "relu-after-matmul": chain.ordered_reference(first),
        "relu-after-sum": [max(x, 0.0) for x in fp.ordered_reference(first)],
        "missing-join": [0.0] * 33,
    }
    witnesses = {
        name: sum(
            abs(Fraction(x) - exact) > budget
            for x, (exact, budget) in zip(values, refs[0], strict=True)
        )
        for name, values in wrong.items()
    }
    if not rounded or not all(witnesses.values()):
        raise BoundedCompilerEmissionError("fan-in numeric witness missing")
    return {
        "schema_version": "tuc.fanin_candidate_numeric.v0",
        "contract_digest": _digest_payload(CONTRACT),
        "corpus_digest": _digest_payload(cases),
        "ordered_oracle_digest": _digest_payload(ordered),
        "exact_reference_digests": [
            _digest_payload([[str(x), str(e)] for x, e in r]) for r in refs
        ],
        "case_count": 10,
        "planned_runs": 11,
        "planned_scalar_checks_per_profile": 363,
        "ordered_oracle_rounding_witnesses": rounded,
        "first_case_fault_witnesses": witnesses,
        "raw_values_serialized": False,
        "native_execution_observed": False,
    }


def artifact_files():
    plans = {p: snapshot(p) for p in PROFILES}
    if len({p["hac_ir"] for p in plans.values()}) != 1:
        raise BoundedCompilerEmissionError("fan-in placement changed HAC-IR")
    report = {
        "schema_version": "tuc.fanin_candidate_report.v0",
        "status": "PASS",
        "scope": "pure_source_plan_numeric_candidate",
        "source_module_digest": _digest_text(SOURCE),
        "source_intent_digest": INTENT_DIGEST,
        "numeric": numeric_summary(),
        "profiles": [
            {
                "profile": p,
                "plan_digest": _digest_payload(v),
                "planned_copy_bytes": v["planned_copy_bytes"],
                "planned_buffer_bytes": v["planned_buffer_bytes"],
            }
            for p, v in plans.items()
        ],
        "native_execution_observed": False,
        "normal_runtime_admission": False,
        "blocked_claims": BLOCKED_CLAIMS,
    }
    values = {
        "report": report,
        "source_intent": parse_source(),
        "numeric_contract": CONTRACT,
        **{f"{p}_plan": v for p, v in plans.items()},
    }
    for value in values.values():
        _bounded_metadata(value)
    return {n + ".json": json.dumps(v, indent=2, sort_keys=True) + "\n" for n, v in values.items()}


def verify_artifacts():
    files = artifact_files()
    for name, value in files.items():
        if _read_bounded_file(CONTEXT / name) != value.encode():
            raise BoundedCompilerEmissionError("fan-in candidate artifact drift")
    return json.loads(files["report.json"])


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        print(json.dumps(verify_artifacts(), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError):
        print("bounded fan-in candidate rejected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
