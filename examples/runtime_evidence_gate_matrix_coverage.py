"""Emit Runtime Evidence Gate Matrix coverage as deterministic JSON."""

from examples.runtime_evidence_gate import build_gate_matrix_coverage_report
from tuc import (
    RuntimeEvidenceGateMatrixCoverageReport,
    dump_runtime_evidence_gate_matrix_coverage_report,
)


def build_report_object() -> RuntimeEvidenceGateMatrixCoverageReport:
    """Return the current Runtime Evidence Gate Matrix coverage audit."""

    return build_gate_matrix_coverage_report()


def build_report() -> str:
    """Return the stable serialized Runtime Evidence Gate Matrix coverage audit."""

    return dump_runtime_evidence_gate_matrix_coverage_report(build_report_object())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
