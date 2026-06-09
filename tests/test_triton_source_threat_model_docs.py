from __future__ import annotations

from pathlib import Path


def test_triton_source_threat_model_blocks_execution_surfaces() -> None:
    text = Path("docs/TRITON_SOURCE_THREAT_MODEL.md").read_text(encoding="utf-8")

    for expected in (
        "Direct Triton source ingestion remains blocked",
        "must not import user modules",
        "must not evaluate decorators",
        "must not execute `@triton.jit`",
        "never import user modules",
        "never evaluate decorators",
        "never execute `@triton.jit`",
        "never compile Python bytecode",
        "never inspect Python function objects",
        "never execute generated artifacts",
        "never access devices",
        "never touch the network",
    ):
        assert expected in text


def test_triton_source_threat_model_requires_resource_budgets_and_negatives() -> None:
    text = Path("docs/TRITON_SOURCE_THREAT_MODEL.md").read_text(encoding="utf-8")

    for expected in (
        "Source bytes",
        "AST nodes",
        "AST depth",
        "Diagnostics",
        "Required Negative Tests",
        "fuzz corpus",
        "arbitrary decorators",
        "ambiguous softmax axis intent",
        "hardware-specific `tuc.*` leakage",
    ):
        assert expected in text


def test_triton_source_threat_model_rfc_preserves_parser_gate() -> None:
    text = Path("rfcs/0049-triton-source-threat-model.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "This RFC does not add a source parser",
        "Direct Triton source ingestion remains blocked",
        "bounded source parser",
        "bounded source parsing",
        "must not import user modules",
        "must not evaluate decorators",
        "must not execute `@triton.jit`",
        "no decorator evaluation",
        "no `@triton.jit` execution",
        "no Python function-object inspection",
        "fuzz corpus or property-test corpus",
        "HAC-IR neutrality",
        "Metadata intake remains the only accepted Triton-like frontend path",
    ):
        assert expected in text


def test_triton_source_threat_model_preserves_data_only_parser_pipeline() -> None:
    docs_text = Path("docs/TRITON_SOURCE_THREAT_MODEL.md").read_text(
        encoding="utf-8"
    )
    rfc_text = Path("rfcs/0049-triton-source-threat-model.md").read_text(
        encoding="utf-8"
    )

    for text in (docs_text, rfc_text):
        assert (
            "source text -> bounded syntax data -> canonical source-intent IR "
            "-> schema-versioned metadata"
        ) in text

    assert "HAC-IR neutrality review result" in docs_text
    assert "must preserve HAC-IR neutrality" in docs_text
