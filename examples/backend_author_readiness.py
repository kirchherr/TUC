"""Emit backend author readiness evidence for the external-vector toy backend."""

try:
    from examples.external_backend_author_path import run_external_backend_author_path
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from external_backend_author_path import run_external_backend_author_path

from tuc import BackendAuthorReadinessReport, dump_backend_author_readiness_report


def build_external_vector_backend_author_readiness() -> BackendAuthorReadinessReport:
    """Return the external-vector backend author readiness report."""

    return run_external_backend_author_path().readiness


def main() -> None:
    report = build_external_vector_backend_author_readiness()
    print(dump_backend_author_readiness_report(report), end="")


if __name__ == "__main__":
    main()
