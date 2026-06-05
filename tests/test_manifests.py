from __future__ import annotations

import json
from pathlib import Path

import pytest

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.manifests import (
    BACKEND_CAPABILITY_SCHEMA_VERSION,
    MAX_MANIFEST_BYTES,
    TRANSFER_COST_PROFILE_SCHEMA_VERSION,
    ManifestError,
    load_backend_capability_manifest,
    load_json_manifest,
    load_transfer_cost_profile_manifest,
)


def test_load_backend_capability_manifest(tmp_path: Path) -> None:
    path = tmp_path / "backend.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": BACKEND_CAPABILITY_SCHEMA_VERSION,
                "name": "manifest-linear",
                "supported_ops": ["matmul", "elementwise"],
                "supports_noise_model": True,
                "supports_calibration": False,
                "preferred_for": ["matmul"],
                "max_error_budget": 0.05,
                "memory_domain": "analog_weight_bank",
                "supported_layouts": ["row_major", "blocked"],
                "produced_layouts": ["row_major"],
            }
        ),
        encoding="utf-8",
    )

    capability = load_backend_capability_manifest(path)

    assert capability.name == "manifest-linear"
    assert capability.supported_ops == frozenset(
        {OperationKind.MATMUL, OperationKind.ELEMENTWISE}
    )
    assert capability.preferred_for == frozenset({OperationKind.MATMUL})
    assert capability.memory_domain is MemoryDomainKind.ANALOG_WEIGHT_BANK
    assert capability.supported_layouts == frozenset(
        {LayoutKind.ROW_MAJOR, LayoutKind.BLOCKED}
    )
    assert capability.produced_layouts == frozenset({LayoutKind.ROW_MAJOR})


def test_load_transfer_cost_profile_manifest(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": TRANSFER_COST_PROFILE_SCHEMA_VERSION,
                "name": "calibrated_v0",
                "fallback": {
                    "bandwidth_gb_s": 10.0,
                    "base_latency_ns": 1000.0,
                    "energy_pj_per_byte": 5.0,
                },
                "edges": [
                    {
                        "source_domain": "analog_weight_bank",
                        "target_domain": "gpu_hbm",
                        "bandwidth_gb_s": 128.0,
                        "base_latency_ns": 2500.0,
                        "energy_pj_per_byte": 12.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    profile = load_transfer_cost_profile_manifest(path)
    estimate = profile.estimate(
        bytes_moved=1024,
        source_domain=MemoryDomainKind.ANALOG_WEIGHT_BANK,
        target_domain=MemoryDomainKind.GPU_HBM,
    )

    assert estimate.estimated_latency_ns == pytest.approx(2508.0)
    assert estimate.estimated_energy_pj == pytest.approx(12288.0)


def test_manifest_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"schema_version":"one","schema_version":"two"}',
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="duplicate keys"):
        load_json_manifest(path)


def test_manifest_loader_rejects_non_finite_json_constant(tmp_path: Path) -> None:
    path = tmp_path / "nan.json"
    path.write_text(
        """
        {
          "schema_version": "tuc.transfer_cost_profile.v0",
          "name": "bad",
          "fallback": {
            "bandwidth_gb_s": NaN,
            "base_latency_ns": 0,
            "energy_pj_per_byte": 0
          },
          "edges": []
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="non-finite"):
        load_transfer_cost_profile_manifest(path)


def test_manifest_loader_rejects_oversized_file(tmp_path: Path) -> None:
    path = tmp_path / "large.json"
    path.write_text(" " * (MAX_MANIFEST_BYTES + 1), encoding="utf-8")

    with pytest.raises(ManifestError, match="size limit"):
        load_json_manifest(path)


def test_manifest_loader_rejects_unknown_schema(tmp_path: Path) -> None:
    path = tmp_path / "backend.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "tuc.backend_capability.v99",
                "name": "backend",
                "supported_ops": ["matmul"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="schema_version"):
        load_backend_capability_manifest(path)


def test_backend_manifest_rejects_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "backend.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": BACKEND_CAPABILITY_SCHEMA_VERSION,
                "name": "backend",
                "supported_ops": ["matmul"],
                "plugin_module": "do_not_import_me",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="unsupported keys"):
        load_backend_capability_manifest(path)


def test_manifest_loader_rejects_non_json_suffix(tmp_path: Path) -> None:
    path = tmp_path / "backend.txt"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ManifestError, match=".json"):
        load_json_manifest(path)
