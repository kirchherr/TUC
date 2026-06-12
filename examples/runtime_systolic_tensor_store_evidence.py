"""Emit Runtime Tensor Store evidence for the systolic execution proof."""

from examples.proof_of_systolic_execution import run_proof
from tuc import (
    RuntimeTensorStoreEvidenceReport,
    build_runtime_tensor_store_evidence_report,
    dump_runtime_tensor_store_evidence_report,
)


def build_systolic_tensor_store_evidence_report() -> RuntimeTensorStoreEvidenceReport:
    """Return the systolic proof tensor-store evidence report."""

    proof = run_proof()
    return build_runtime_tensor_store_evidence_report(
        proof.compiled.hac_ir.graph,
        proof.compiled.partition_plan,
        proof.execution,
    )


def build_report() -> str:
    """Return the stable serialized systolic Runtime Tensor Store evidence report."""

    return dump_runtime_tensor_store_evidence_report(
        build_systolic_tensor_store_evidence_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
