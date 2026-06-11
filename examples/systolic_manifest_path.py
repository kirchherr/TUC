"""Proof that a systolic capability can enter TUC as declarative data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from tuc.backends.registry import BackendRegistry
from tuc.compiler import CompilationResult, compile_graph
from tuc.ir import ComputeGraph, ComputeOperation, LayoutKind, OperationKind, TensorRef
from tuc.reference import reference_elementwise, reference_matmul
from tuc.runtime import (
    RuntimeExecutionReadinessReport,
    RuntimeExecutionResult,
    execute_graph,
    runtime_execution_readiness_report,
)

MANIFEST_PATH = Path(__file__).with_name("manifests") / "systolic_sim_backend.json"

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class SystolicManifestPathReport:
    """Reviewable outputs from the systolic manifest author path."""

    registry: BackendRegistry
    graph: ComputeGraph
    compiled: CompilationResult
    readiness: RuntimeExecutionReadinessReport
    execution: RuntimeExecutionResult
    result: FloatArray
    reference: FloatArray
    passed: bool


def build_graph() -> ComputeGraph:
    """Build a graph that separates accelerator and host work."""

    lhs = TensorRef("lhs", (2, 3))
    rhs = TensorRef("rhs", (3, 2))
    projection = TensorRef("projection", (2, 2))
    activated = TensorRef("activated", (2, 2))
    return ComputeGraph(
        name="systolic_manifest_path",
        operations=(
            ComputeOperation(
                name="manifest_systolic_projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(projection,),
            ),
            ComputeOperation(
                name="manifest_host_activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(projection,),
                outputs=(activated,),
                attributes={"kernel": "relu"},
            ),
        ),
    )


def proof_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite inputs for the proof."""

    return {
        "lhs": np.array([[1.0, 2.0, -1.0], [3.0, -2.0, 0.5]], dtype=np.float64),
        "rhs": np.array([[2.0, -1.0], [0.5, 1.0], [4.0, -3.0]], dtype=np.float64),
    }


def reference_result(inputs: dict[str, FloatArray]) -> FloatArray:
    """Return the independent reference result for the proof graph."""

    return reference_elementwise(reference_matmul(inputs["lhs"], inputs["rhs"]), "relu")


def run_systolic_manifest_path(
    manifest_path: Path = MANIFEST_PATH,
) -> SystolicManifestPathReport:
    """Run manifest loading, planning, readiness, execution, and comparison."""

    registry = BackendRegistry.from_manifest_paths([manifest_path])
    graph = build_graph()
    compiled = compile_graph(graph, registry.capabilities())
    readiness = runtime_execution_readiness_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )
    inputs = proof_inputs()
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
    result = execution.output_for("activated")
    expected = reference_result(inputs)
    passed = np.allclose(result, expected, rtol=1e-12, atol=1e-12)
    return SystolicManifestPathReport(
        registry=registry,
        graph=graph,
        compiled=compiled,
        readiness=readiness,
        execution=execution,
        result=result,
        reference=expected,
        passed=passed,
    )


def render_systolic_manifest_path_report(report: SystolicManifestPathReport) -> str:
    """Render deterministic text for tests and review."""

    registration = report.registry.registrations()[0]
    capability = registration.capability
    lines = ["== manifest =="]
    lines.append(f"source_label: {registration.source_label}")
    lines.append(f"name: {capability.name}")
    lines.append(f"supported_ops: {_format_enum_values(capability.supported_ops)}")
    lines.append(f"preferred_for: {_format_enum_values(capability.preferred_for)}")
    lines.append(f"memory_domain: {capability.memory_domain.value}")
    lines.append(f"supported_layouts: {_format_enum_values(capability.supported_layouts)}")
    lines.append(f"produced_layouts: {_format_enum_values(capability.produced_layouts)}")

    lines.append("")
    lines.append("== support diagnostics ==")
    for operation in report.graph.operations:
        for diagnostic in report.registry.diagnose_operation_support(operation):
            lines.append(
                f"{diagnostic.backend_name}:{diagnostic.operation_name} "
                f"{diagnostic.reason} {diagnostic.detail}"
            )

    lines.append("")
    lines.append("== backend assignments ==")
    for assignment in report.compiled.partition_plan.assignments:
        lines.append(f"{assignment.operation_name} -> {assignment.backend_name}")

    lines.append("")
    lines.append("== transfer plan ==")
    lines.append(report.compiled.dump_runtime_plan())

    lines.append("")
    lines.append("== execution readiness ==")
    lines.append(report.readiness.dump())

    lines.append("")
    lines.append("== execution trace ==")
    lines.append(report.execution.trace.dump())

    lines.append("")
    lines.append("== result ==")
    lines.append(_format_array(report.result))

    lines.append("")
    lines.append("== reference result ==")
    lines.append(_format_array(report.reference))

    lines.append("")
    lines.append("PASS" if report.passed else "FAIL")
    return "\n".join(lines)


def main() -> None:
    report = run_systolic_manifest_path()
    print(render_systolic_manifest_path_report(report))
    if not report.passed:
        raise SystemExit(1)


def _format_array(value: FloatArray) -> str:
    return np.array2string(value, precision=6, suppress_small=False)


def _format_enum_values(values: frozenset[OperationKind] | frozenset[LayoutKind]) -> str:
    return ",".join(sorted(value.value for value in values))


if __name__ == "__main__":
    main()
