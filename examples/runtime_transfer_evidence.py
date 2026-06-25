"""Emit Runtime Transfer Evidence v0."""

from examples.runtime_backend_equivalence import build_graph
from tuc import SystolicArraySimulatorBackend, compile_graph
from tuc.runtime.transfer_evidence import (
    RuntimeTransferEvidenceReport,
    build_runtime_transfer_evidence_report,
    dump_runtime_transfer_evidence_report,
)


def build_current_runtime_transfer_evidence_report() -> RuntimeTransferEvidenceReport:
    """Return the current data-only runtime-transfer evidence report."""

    graph = build_graph()
    compiled = compile_graph(graph, (SystolicArraySimulatorBackend().capability,))
    return build_runtime_transfer_evidence_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )


def build_report() -> str:
    """Return the stable serialized runtime-transfer evidence report."""

    return dump_runtime_transfer_evidence_report(build_current_runtime_transfer_evidence_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
