"""Executable negative-test template for TUC backend authors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tuc.backends.base import BackendCapability, LoweringResult
from tuc.ir.memory import LayoutKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.manifests import (
    BACKEND_CAPABILITY_SCHEMA_VERSION,
    ManifestError,
    load_backend_capability_manifest,
    load_json_manifest,
)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("plugin_module", "vendor_backend"),
        ("import_path", "vendor.backend:load"),
        ("shell_command", "vendor-tool --compile"),
        ("dynamic_library", "vendor_backend.dll"),
        ("device_path", "/dev/vendor0"),
        ("network_endpoint", "https://backend.example.invalid"),
        ("artifact_output_path", "/tmp/backend-artifacts"),
    ),
)
def test_backend_manifest_rejects_execution_surface_fields(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    manifest = {
        "schema_version": BACKEND_CAPABILITY_SCHEMA_VERSION,
        "name": "candidate",
        "supported_ops": ["matmul"],
        field: value,
    }
    path = tmp_path / "candidate_backend.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ManifestError, match="unsupported keys"):
        load_backend_capability_manifest(path)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("bandwidth_gb_s", 128.0),
        ("base_latency_ns", 2500.0),
        ("energy_pj_per_byte", 12.0),
        ("calibration_data", "device-run-2026-06-08.json"),
        ("hardware_serial", "vendor-device-0"),
        ("benchmark_score", "fastest"),
        ("hardware_certificate", "certified"),
        ("measured_error", 0.001),
        ("noise_model_module", "vendor.noise_model"),
    ),
)
def test_backend_manifest_rejects_misleading_capability_claim_fields(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    manifest = {
        "schema_version": BACKEND_CAPABILITY_SCHEMA_VERSION,
        "name": "candidate",
        "supported_ops": ["matmul"],
        field: value,
    }
    path = tmp_path / "candidate_backend.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ManifestError, match="unsupported keys"):
        load_backend_capability_manifest(path)


def test_backend_manifest_rejects_negative_error_budget(tmp_path: Path) -> None:
    path = tmp_path / "candidate_backend.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": BACKEND_CAPABILITY_SCHEMA_VERSION,
                "name": "candidate",
                "supported_ops": ["matmul"],
                "max_error_budget": -0.1,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="finite and non-negative"):
        load_backend_capability_manifest(path)


def test_backend_manifest_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "candidate_backend.json"
    path.write_text(
        """
        {
          "schema_version": "tuc.backend_capability.v0",
          "name": "candidate",
          "name": "shadowed",
          "supported_ops": ["matmul"]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="duplicate keys"):
        load_json_manifest(path)


def test_backend_manifest_rejects_unknown_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "candidate_backend.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "tuc.backend_capability.v99",
                "name": "candidate",
                "supported_ops": ["matmul"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="schema_version"):
        load_backend_capability_manifest(path)


def test_backend_capability_rejects_false_preferred_operation_claim() -> None:
    with pytest.raises(ValueError, match="preferred_for must be a subset"):
        BackendCapability(
            name="candidate",
            supported_ops=frozenset({OperationKind.ELEMENTWISE}),
            preferred_for=frozenset({OperationKind.MATMUL}),
        )


def test_backend_capability_rejects_unsupported_layout_claim() -> None:
    operation = ComputeOperation(
        name="blocked_activation",
        kind=OperationKind.ELEMENTWISE,
        inputs=(TensorRef("x", (8, 8)),),
        outputs=(TensorRef("y", (8, 8)),),
        attributes={"tuc.layout": LayoutKind.BLOCKED.value},
    )
    capability = BackendCapability(
        name="row_major_only",
        supported_ops=frozenset({OperationKind.ELEMENTWISE}),
        supported_layouts=frozenset({LayoutKind.ROW_MAJOR}),
    )

    assert capability.supports(operation) is False


class _TemplateBackend:
    """Tiny backend authors can copy when writing lower-time rejection tests."""

    def __init__(self) -> None:
        self._capability = BackendCapability(
            name="template",
            supported_ops=frozenset({OperationKind.MATMUL}),
        )

    @property
    def capability(self) -> BackendCapability:
        return self._capability

    def lower(self, graph: ComputeGraph) -> LoweringResult:
        unsupported = [
            operation.name
            for operation in graph.operations
            if not self.capability.supports(operation)
        ]
        if unsupported:
            raise ValueError("backend cannot lower: " + ", ".join(unsupported))
        return LoweringResult(
            backend_name=self.capability.name,
            graph_name=graph.name,
            artifact="# template artifact",
        )


def test_backend_lowering_rejects_unsupported_operations() -> None:
    graph = ComputeGraph(
        name="unsupported",
        operations=(
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(TensorRef("x", (8, 8)),),
                outputs=(TensorRef("y", (8, 8)),),
            ),
        ),
    )

    with pytest.raises(ValueError, match="backend cannot lower: activation"):
        _TemplateBackend().lower(graph)
