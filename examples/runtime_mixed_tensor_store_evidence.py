"""Emit Runtime Tensor Store evidence for mixed accelerator placement."""

from __future__ import annotations

from examples.runtime_mixed_backend_equivalence import build_graph, proof_inputs
from tuc import (
    RuntimeTensorStoreEvidenceReport,
    SystolicArraySimulatorBackend,
    VectorSimulatorBackend,
    build_runtime_tensor_store_evidence_report,
    compile_graph,
    dump_runtime_tensor_store_evidence_report,
    execute_graph,
)


def build_mixed_tensor_store_evidence_report() -> RuntimeTensorStoreEvidenceReport:
    """Return tensor-store evidence for the accepted mixed accelerator plan."""

    compiled = compile_graph(
        build_graph(),
        [
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    execution = execute_graph(
        compiled.hac_ir.graph,
        compiled.partition_plan,
        proof_inputs(),
    )
    return build_runtime_tensor_store_evidence_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
        execution,
    )


def build_report() -> str:
    """Return the stable serialized mixed Runtime Tensor Store evidence report."""

    return dump_runtime_tensor_store_evidence_report(
        build_mixed_tensor_store_evidence_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
