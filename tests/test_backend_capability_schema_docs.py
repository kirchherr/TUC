from __future__ import annotations

from pathlib import Path

from tuc.manifests import (
    BACKEND_CAPABILITY_SCHEMA_VERSION,
    TRANSFER_COST_PROFILE_SCHEMA_VERSION,
)


def test_backend_capability_schema_doc_covers_manifest_fields() -> None:
    text = Path("docs/BACKEND_CAPABILITY_SCHEMA.md").read_text(encoding="utf-8")

    for field in (
        "schema_version",
        "name",
        "supported_ops",
        "supports_noise_model",
        "supports_calibration",
        "preferred_for",
        "max_error_budget",
        "memory_domain",
        "supported_layouts",
        "produced_layouts",
    ):
        assert f"`{field}`" in text


def test_backend_capability_schema_doc_covers_planning_assumptions() -> None:
    text = Path("docs/BACKEND_CAPABILITY_SCHEMA.md").read_text(encoding="utf-8")

    assert BACKEND_CAPABILITY_SCHEMA_VERSION in text
    assert TRANSFER_COST_PROFILE_SCHEMA_VERSION in text
    assert "`bandwidth_gb_s`" in text
    assert "`base_latency_ns`" in text
    assert "`energy_pj_per_byte`" in text
    assert "Calibration data" in text
    assert "correctness proof" in text
    assert "not proof of real" in text
    assert "hardware performance" in text


def test_backend_capability_schema_doc_states_security_boundary() -> None:
    text = Path("docs/BACKEND_CAPABILITY_SCHEMA.md").read_text(encoding="utf-8")

    for forbidden_surface in (
        "discover plugins",
        "import modules",
        "spawn subprocesses",
        "load dynamic libraries",
        "touch devices",
        "execute generated artifacts",
    ):
        assert forbidden_surface in text


def test_backend_capability_schema_doc_covers_negative_examples() -> None:
    text = Path("docs/BACKEND_CAPABILITY_SCHEMA.md").read_text(encoding="utf-8")

    assert "Invalid Or Misleading Examples" in text
    for misplaced_field in (
        "`tuc.transfer_cost_profile.v0`",
        "calibration_data",
        "hardware_serial",
        "benchmark_score",
        "hardware_certificate",
        "max_error_budget",
    ):
        assert misplaced_field in text
