from __future__ import annotations

from pathlib import Path


def test_triton_source_preflight_doc_preserves_execution_free_boundary() -> None:
    text = Path("docs/TRITON_SOURCE_PREFLIGHT.md").read_text(encoding="utf-8")

    for expected in (
        "This is not a Triton source parser",
        "not a `@triton.jit` handler",
        "not an ingestion path into `ComputeGraph`",
        "must not import user modules",
        "must not evaluate decorators",
        "must not produce a `ComputeGraph`",
        "The only accepted decorator syntax is `@triton.jit` as data",
        "Decorator calls such as `@triton.jit(...)` are rejected",
    ):
        assert expected in text


def test_triton_source_preflight_rfc_preserves_parser_gate() -> None:
    text = Path("rfcs/0050-triton-source-preflight-v0.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "This RFC does not add direct Triton source ingestion",
        "bounded source syntax preflight",
        "must not import user modules",
        "must not evaluate decorators",
        "must not execute `@triton.jit`",
        "must not produce a `ComputeGraph`",
        "deterministic golden source preflight report",
        "Metadata intake remains the only source of `ComputeGraph` values",
    ):
        assert expected in text


def test_triton_source_threat_model_allows_only_diagnostic_preflight() -> None:
    text = Path("docs/TRITON_SOURCE_THREAT_MODEL.md").read_text(encoding="utf-8")

    for expected in (
        "The only Triton-like frontend path accepted by TUC for compiler ingestion",
        "Triton Source Preflight",
        "bounded syntax data",
        "must not produce metadata",
        "`ComputeGraph`, TLIR, HAC-IR, HS-IR",
    ):
        assert expected in text
