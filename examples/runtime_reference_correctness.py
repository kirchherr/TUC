"""Emit data-only Runtime Reference Correctness for the execution proof."""

from examples.proof_of_execution import run_proof
from tuc import (
    RuntimeReferenceCorrectnessReport,
    dump_runtime_reference_correctness_report,
)


def build_reference_correctness_report() -> RuntimeReferenceCorrectnessReport:
    """Return the current proof-of-execution reference correctness report."""

    return run_proof().correctness


def build_report() -> str:
    """Return the stable serialized Runtime Reference Correctness report."""

    return dump_runtime_reference_correctness_report(
        build_reference_correctness_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
