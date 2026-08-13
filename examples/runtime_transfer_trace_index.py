"""Emit Runtime Transfer Trace Index v0."""

from examples.runtime_backend_equivalence import build_graph, proof_inputs
from tuc import SystolicArraySimulatorBackend, compile_graph
from tuc.report_output import emit_public_json_report
from tuc.runtime.executor import execute_graph
from tuc.runtime.transfer_evidence import build_runtime_transfer_evidence_report
from tuc.runtime.transfer_trace_index import (
    RuntimeTransferTraceIndexReport,
    build_runtime_transfer_trace_index_report,
    dump_runtime_transfer_trace_index_report,
)


def build_current_runtime_transfer_trace_index_report() -> (
    RuntimeTransferTraceIndexReport
):
    """Return the current data-only runtime-transfer trace index."""

    graph = build_graph()
    compiled = compile_graph(graph, (SystolicArraySimulatorBackend().capability,))
    execution = execute_graph(
        compiled.hac_ir.graph,
        compiled.partition_plan,
        proof_inputs(),
    )
    evidence = build_runtime_transfer_evidence_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )
    return build_runtime_transfer_trace_index_report(evidence, execution.trace)


def build_report() -> str:
    """Return the stable serialized runtime-transfer trace index."""

    return dump_runtime_transfer_trace_index_report(
        build_current_runtime_transfer_trace_index_report()
    )


def main() -> None:
    emit_public_json_report(build_report())


if __name__ == "__main__":
    main()
