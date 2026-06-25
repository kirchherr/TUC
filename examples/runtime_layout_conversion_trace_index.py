"""Emit Runtime Layout Conversion Trace Index v0."""

try:
    from examples.runtime_mixed_backend_equivalence import build_graph, proof_inputs
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_mixed_backend_equivalence import (  # type: ignore[no-redef]
        build_graph,
        proof_inputs,
    )

from tuc import SystolicArraySimulatorBackend, VectorSimulatorBackend, compile_graph
from tuc.runtime.executor import execute_graph
from tuc.runtime.layout_conversion_evidence import (
    build_runtime_layout_conversion_evidence_report,
)
from tuc.runtime.layout_conversion_trace_index import (
    RuntimeLayoutConversionTraceIndexReport,
    build_runtime_layout_conversion_trace_index_report,
    dump_runtime_layout_conversion_trace_index_report,
)


def build_current_runtime_layout_conversion_trace_index_report() -> (
    RuntimeLayoutConversionTraceIndexReport
):
    """Return the current data-only layout-conversion trace index."""

    graph = build_graph()
    compiled = compile_graph(
        graph,
        (
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ),
    )
    execution = execute_graph(
        compiled.hac_ir.graph,
        compiled.partition_plan,
        proof_inputs(),
    )
    evidence = build_runtime_layout_conversion_evidence_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )
    return build_runtime_layout_conversion_trace_index_report(
        evidence,
        execution.trace,
    )


def build_report() -> str:
    """Return the stable serialized layout-conversion trace index."""

    return dump_runtime_layout_conversion_trace_index_report(
        build_current_runtime_layout_conversion_trace_index_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
