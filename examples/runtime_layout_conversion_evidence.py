"""Emit Runtime Layout Conversion Evidence v0."""

try:
    from examples.runtime_mixed_backend_equivalence import build_graph
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_mixed_backend_equivalence import build_graph  # type: ignore[no-redef]

from tuc import SystolicArraySimulatorBackend, VectorSimulatorBackend, compile_graph
from tuc.runtime.layout_conversion_evidence import (
    RuntimeLayoutConversionEvidenceReport,
    build_runtime_layout_conversion_evidence_report,
    dump_runtime_layout_conversion_evidence_report,
)


def build_current_runtime_layout_conversion_evidence_report() -> (
    RuntimeLayoutConversionEvidenceReport
):
    """Return the current data-only layout-conversion evidence report."""

    graph = build_graph()
    compiled = compile_graph(
        graph,
        (
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ),
    )
    return build_runtime_layout_conversion_evidence_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )


def build_report() -> str:
    """Return the stable serialized layout-conversion evidence report."""

    return dump_runtime_layout_conversion_evidence_report(
        build_current_runtime_layout_conversion_evidence_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
