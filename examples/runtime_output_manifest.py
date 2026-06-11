"""Emit the Runtime Output Manifest for the current execution proof."""

from examples.proof_of_execution import run_proof
from tuc import (
    RuntimeOutputManifestReport,
    build_runtime_output_manifest_report,
    dump_runtime_output_manifest_report,
)


def build_output_manifest_report() -> RuntimeOutputManifestReport:
    """Return the current proof-of-execution output manifest report."""

    proof = run_proof()
    return build_runtime_output_manifest_report(
        proof.compiled.hac_ir.graph,
        proof.execution,
    )


def build_report() -> str:
    """Return the stable serialized Runtime Output Manifest report."""

    return dump_runtime_output_manifest_report(build_output_manifest_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
