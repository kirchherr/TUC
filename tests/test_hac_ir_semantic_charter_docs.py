from __future__ import annotations

from pathlib import Path


def _charter_text() -> str:
    return Path("docs/HAC_IR_SEMANTIC_CHARTER.md").read_text(encoding="utf-8")


def test_hac_ir_semantic_charter_defines_four_categories() -> None:
    text = _charter_text()

    for category in (
        "Compute Intent",
        "Compiler Facts",
        "Planning Constraints",
        "Forbidden Backend Details",
    ):
        assert category in text


def test_hac_ir_semantic_charter_covers_current_hac_attributes() -> None:
    text = _charter_text()

    for attribute in (
        "tuc.semantic_op",
        "tuc.source_stage",
        "tuc.linearity",
        "tuc.arithmetic_ops",
        "tuc.bytes_read",
        "tuc.bytes_written",
        "tuc.arithmetic_intensity",
        "tuc.layout",
        "tuc.layout_tile_shape",
        "tuc.layout_alignment_bytes",
        "tuc.movement_notes",
        "tuc.max_error_budget",
        "tuc.preferred_memory_domain",
    ):
        assert f"`{attribute}`" in text


def test_hac_ir_semantic_charter_keeps_backend_surfaces_out() -> None:
    text = _charter_text()

    for forbidden in (
        "Backend assignment",
        "Vendor names",
        "Device identifiers",
        "Plugin entrypoints",
        "dynamic libraries",
        "generated artifacts",
        "Calibration evidence",
        "benchmark results",
        "hardware certificates",
        "HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES",
    ):
        assert forbidden in text


def test_hac_ir_semantic_charter_links_to_review_boundary() -> None:
    text = _charter_text()

    assert "HAC_IR_NEUTRALITY.md" in text
    assert "Would the value still make sense if all current backends disappeared?" in text
    assert "If the value is useful only for one backend family" in text
