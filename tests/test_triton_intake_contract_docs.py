from __future__ import annotations

from pathlib import Path


def test_frontend_adapter_doc_covers_intake_contract() -> None:
    text = Path("docs/FRONTEND_ADAPTER.md").read_text(encoding="utf-8")

    for expected in (
        "Schema-versioned metadata through `triton_metadata.v0`",
        "`TritonIntakeReport`",
        "Unsupported `schema_version` values are rejected",
        "Known execution-surface fields",
        "`generated_artifact`",
    ):
        assert expected in text


def test_triton_intake_rfc_preserves_execution_free_boundary() -> None:
    text = Path("rfcs/0046-triton-intake-contract.md").read_text(encoding="utf-8")

    for expected in (
        "TRITON_METADATA_SCHEMA_VERSION",
        "TRITON_METADATA_INTAKE_CONTRACT",
        "TritonIntakeReport",
        "no Python imports",
        "no Triton JIT execution",
        "no generated-artifact execution",
        "dedicated threat model",
    ):
        assert expected in text


def test_triton_frontend_golden_rfc_preserves_review_artifacts() -> None:
    text = Path("rfcs/0047-triton-frontend-golden-artifacts.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "tests/golden/frontend/triton_metadata_intake.txt",
        "tests/golden/hac_ir/triton_metadata_mlp.txt",
        "tests/golden/runtime_plans/triton_metadata_mlp.txt",
        "tests/golden/compiler_decisions/triton_metadata_mlp.txt",
        "does not import user modules",
        "Direct `@triton.jit` handling remains blocked",
    ):
        assert expected in text
