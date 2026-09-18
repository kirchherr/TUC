"""Compile four graph families through the same bounded native artifact API.

This default command only produces a compact metadata report. It does not write
source files, run a compiler, import a plugin or access a device.
"""

from __future__ import annotations

import json
from hashlib import sha256

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import BoundedDAGArtifacts, DAGTarget, lower_bounded_dag
from tuc.compiler import CompilationResult, compile_graph
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.runtime import RuntimeOverrideAction, RuntimeOverrideRule, RuntimeOverrideSet

FAMILIES = ("chain", "fanout", "fanin", "diamond")
SHAPES = ((1, 1, 1), (5, 3, 4), (33, 7, 5))


def graph_for(family: str, shape: tuple[int, int, int] = (5, 3, 4)) -> ComputeGraph:
    """Construct public typed compute intent, including an unseen joined branch.

The diamond joins two ReLU producers, fans its projection out to a direct Sum
and ReLU, joins that ReLU with a third input at a second Matmul, and publishes
two row sums. Kernel generation has no knowledge of these family names.
"""
    if type(family) is not str or family not in FAMILIES:
        raise ValueError("unknown bounded DAG portfolio family")
    if (
        type(shape) is not tuple
        or len(shape) != 3
        or any(type(d) is not int or not 1 <= d <= 64 for d in shape)
    ):
        raise ValueError("bounded DAG portfolio shape rejected")
    rows, inner, columns = shape
    a, b = TensorRef("a", (rows, inner)), TensorRef("b", (inner, columns))
    projection = TensorRef("projection", (rows, columns))
    activated = TensorRef("activated", projection.shape)
    row_sum = TensorRef("row_sum", (rows,))

    def relu(name: str, source: TensorRef, result: TensorRef) -> ComputeOperation:
        return ComputeOperation(
            name, OperationKind.ELEMENTWISE, (source,), (result,), {"kernel": "relu"}
        )

    def dot(
        name: str, left: TensorRef, right: TensorRef, result: TensorRef
    ) -> ComputeOperation:
        return ComputeOperation(name, OperationKind.MATMUL, (left, right), (result,))

    def reduce(name: str, source: TensorRef, result: TensorRef) -> ComputeOperation:
        return ComputeOperation(name, OperationKind.REDUCTION, (source,), (result,), {"axis": 1})

    if family in ("chain", "fanout"):
        operations = [dot("project", a, b, projection), relu("activate", projection, activated)]
        if family == "fanout":
            operations.append(reduce("raw_sum", projection, TensorRef("raw", (rows,))))
        operations.append(reduce("final_sum", activated, row_sum))
    else:
        left, right = TensorRef("left", a.shape), TensorRef("right", b.shape)
        operations = [
            relu("activate_left", a, left),
            relu("activate_right", b, right),
            dot("join", left, right, projection),
        ]
        if family == "diamond":
            weights = TensorRef("weights", (columns, inner))
            second = TensorRef("second", (rows, inner))
            operations.extend([
                relu("activate_join", projection, activated),
                dot("second_join", activated, weights, second),
                reduce("raw_sum", projection, TensorRef("raw", (rows,))),
                reduce("final_sum", second, row_sum),
            ])
        else:
            operations.append(reduce("final_sum", projection, row_sum))
    return ComputeGraph(f"bounded_dag_{family}", tuple(operations))


def compile_case(
    family: str, profile: str, shape: tuple[int, int, int] = (5, 3, 4)
) -> tuple[CompilationResult, BoundedDAGArtifacts]:
    graph = graph_for(family, shape)
    if (
        type(profile) is not str
        or len(profile) != len(graph.operations)
        or any(character not in "cg" for character in profile)
    ):
        raise ValueError("bounded DAG portfolio placement rejected")
    supported = frozenset(
        {OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}
    )
    capabilities = (
        BackendCapability("dag-c11", supported, memory_domain=MemoryDomainKind.HOST_RAM),
        BackendCapability("dag-cuda", supported, memory_domain=MemoryDomainKind.UNKNOWN),
    )
    overrides = RuntimeOverrideSet(tuple(
        RuntimeOverrideRule(
            operation.name,
            RuntimeOverrideAction.REQUIRE_BACKEND,
            "dag-c11" if placement == "c" else "dag-cuda",
        )
        for operation, placement in zip(graph.operations, profile, strict=True)
    ))
    compilation = compile_graph(graph, capabilities, runtime_overrides=overrides)
    targets = {
        assignment.backend_name: (
            DAGTarget.C11 if assignment.backend_name == "dag-c11" else DAGTarget.CUDA_SM86
        )
        for assignment in compilation.partition_plan.assignments
    }
    return compilation, lower_bounded_dag(compilation.hac_ir, compilation.partition_plan, targets)


def portfolio_report() -> dict[str, object]:
    rows = []
    for family in FAMILIES:
        for shape in SHAPES:
            count = len(graph_for(family, shape).operations)
            profiles = ("c" * count, "g" * count, ("gc" * count)[:count])
            for profile in profiles:
                _, artifacts = compile_case(family, profile, shape)
                manifest = json.loads(artifacts.manifest_json)
                rows.append({
                    "family": family,
                    "shape": list(shape),
                    "profile": profile,
                    "manifest_digest": "sha256:" + sha256(
                        artifacts.manifest_json.encode("utf-8")
                    ).hexdigest(),
                    "operations": count,
                    "buffer_bytes": manifest["planned_buffer_bytes"],
                    "copy_bytes": manifest["planned_copy_bytes"],
                })
    return {
        "schema_version": "tuc.bounded_dag_portfolio.v0",
        "status": "PASS",
        "families": list(FAMILIES),
        "artifact_bundles": len(rows),
        "cases": rows,
        "native_execution_observed": False,
        "normal_runtime_admission": False,
        "latency_ns": None,
        "energy_pj": None,
    }


if __name__ == "__main__":
    print(json.dumps(portfolio_report(), sort_keys=True, indent=2))
