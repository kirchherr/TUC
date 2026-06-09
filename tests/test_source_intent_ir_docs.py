from __future__ import annotations

from pathlib import Path


def test_source_intent_doc_preserves_non_lowering_boundary() -> None:
    text = Path("docs/SOURCE_INTENT_IR.md").read_text(encoding="utf-8")

    for expected in (
        "not a Triton source parser",
        "not a metadata adapter",
        "not a `ComputeGraph` constructor",
        "produce metadata",
        "produce a `ComputeGraph`",
        "produce TLIR, HAC-IR, or HS-IR",
        "execute `@triton.jit`",
        "no `to_compute_graph` or `to_metadata`",
        "The preflight must not create Source Intent IR",
    ):
        assert expected in text


def test_source_intent_rfc_preserves_conversion_gate() -> None:
    text = Path("rfcs/0053-canonical-source-intent-ir.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "does not add source parsing",
        "no `to_metadata`",
        "no `to_compute_graph`",
        "no lowering path",
        "hardware family names",
        "reserved `tuc.*` keys",
        "metadata remains the accepted bridge",
        "Future conversion from Source Intent IR to metadata requires its own RFC",
    ):
        assert expected in text


def test_triton_docs_reference_source_intent_without_ingestion() -> None:
    compatibility = Path("docs/TRITON_COMPATIBILITY.md").read_text(
        encoding="utf-8"
    )
    threat_model = Path("docs/TRITON_SOURCE_THREAT_MODEL.md").read_text(
        encoding="utf-8"
    )
    preflight = Path("docs/TRITON_SOURCE_PREFLIGHT.md").read_text(encoding="utf-8")

    assert "Canonical Source Intent IR | L1" in compatibility
    assert "but it is not connected to lowering" in compatibility
    assert "Canonical Source Intent IR v0 now exists only as a data model" in (
        threat_model
    )
    assert "The preflight must not create it" in preflight
