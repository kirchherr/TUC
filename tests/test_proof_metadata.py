from __future__ import annotations

import pytest

from examples.proof_of_reduction import run_proof
from examples.proof_of_softmax import run_proof as run_softmax_proof
from tuc.proof import ProofReportMetadata, proof_metadata_from_partition_plan


def test_proof_metadata_from_partition_plan_is_deterministic() -> None:
    metadata = proof_metadata_from_partition_plan(
        proof_id="proof_of_reduction",
        proof_version="alpha.v1",
        graph_family="reduction",
        partition_plan=run_proof().compiled.partition_plan,
    )

    assert metadata.render_lines() == (
        "report_schema: proof-report.v0",
        "proof_id: proof_of_reduction",
        "proof_version: alpha.v1",
        "graph_family: reduction",
        "backend_set: gpu, linear-sim",
    )


def test_softmax_proof_metadata_from_partition_plan_is_deterministic() -> None:
    metadata = proof_metadata_from_partition_plan(
        proof_id="proof_of_softmax",
        proof_version="alpha.v1",
        graph_family="softmax",
        partition_plan=run_softmax_proof().compiled.partition_plan,
    )

    assert metadata.render_lines() == (
        "report_schema: proof-report.v0",
        "proof_id: proof_of_softmax",
        "proof_version: alpha.v1",
        "graph_family: softmax",
        "backend_set: gpu, linear-sim",
    )


def test_proof_metadata_rejects_empty_backend_set() -> None:
    with pytest.raises(ValueError, match="backend_set must not be empty"):
        ProofReportMetadata(
            proof_id="proof",
            proof_version="alpha.v1",
            graph_family="abstraction",
            backend_set=(),
        )


def test_proof_metadata_rejects_unsafe_identifier() -> None:
    with pytest.raises(ValueError, match="proof_id must be a safe proof identifier"):
        ProofReportMetadata(
            proof_id="../proof",
            proof_version="alpha.v1",
            graph_family="abstraction",
            backend_set=("gpu",),
        )
