"""Emit a deterministic runtime evidence matrix for proof review."""

from tuc import (
    RuntimeEvidenceMatrixReport,
    build_current_runtime_evidence_matrix_report,
    dump_runtime_evidence_matrix_report,
)


def build_matrix_report() -> RuntimeEvidenceMatrixReport:
    """Return the current curated runtime evidence matrix."""

    return build_current_runtime_evidence_matrix_report()


def build_report() -> str:
    """Return the stable serialized matrix report."""

    return dump_runtime_evidence_matrix_report(build_matrix_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
