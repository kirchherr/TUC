"""Emit the Runtime Input Manifest for the current execution proof."""

from examples.proof_of_execution import run_proof
from tuc import (
    RuntimeInputManifestReport,
    build_runtime_input_manifest_report,
    dump_runtime_input_manifest_report,
)


def build_input_manifest_report() -> RuntimeInputManifestReport:
    """Return the current proof-of-execution input manifest report."""

    proof = run_proof()
    return build_runtime_input_manifest_report(
        proof.compiled.hac_ir.graph,
        proof.execution,
    )


def build_report() -> str:
    """Return the stable serialized Runtime Input Manifest report."""

    return dump_runtime_input_manifest_report(build_input_manifest_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
