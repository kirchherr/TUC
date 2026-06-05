from __future__ import annotations

import json
from pathlib import Path

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.registry import (
    MAX_REGISTERED_BACKENDS,
    BackendRegistry,
    BackendRegistryError,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.manifests import BACKEND_CAPABILITY_SCHEMA_VERSION, ManifestError
from tuc.runtime.partitioning import partition_graph


def test_registry_loads_explicit_manifest_capabilities_for_partitioning(
    tmp_path: Path,
) -> None:
    path = tmp_path / "linear-sim.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": BACKEND_CAPABILITY_SCHEMA_VERSION,
                "name": "linear-sim",
                "supported_ops": ["matmul"],
                "preferred_for": ["matmul"],
                "memory_domain": "analog_weight_bank",
            }
        ),
        encoding="utf-8",
    )
    graph = _matmul_graph()

    registry = BackendRegistry.from_manifest_paths([path])
    plan = partition_graph(graph, registry.capabilities())

    assert registry.names() == ("linear-sim",)
    assert registry.registrations()[0].source_label == "linear-sim.json"
    assert registry.capability("linear-sim").memory_domain is MemoryDomainKind.ANALOG_WEIGHT_BANK
    assert plan.backend_for("projection") == "linear-sim"


def test_registry_rejects_duplicate_backend_names(tmp_path: Path) -> None:
    first = _write_backend_manifest(tmp_path / "first.json", name="same")
    second = _write_backend_manifest(tmp_path / "second.json", name="same")

    with pytest.raises(BackendRegistryError, match="duplicate backend"):
        BackendRegistry.from_manifest_paths([first, second])


def test_registry_rejects_unsafe_in_memory_capability_names() -> None:
    capability = BackendCapability(
        name="../plugin",
        supported_ops=frozenset({OperationKind.MATMUL}),
    )

    with pytest.raises(BackendRegistryError, match="safe registry identifier"):
        BackendRegistry.from_capabilities([capability])


def test_registry_rejects_excessive_backend_count() -> None:
    capabilities = tuple(
        BackendCapability(
            name=f"backend-{index}",
            supported_ops=frozenset({OperationKind.MATMUL}),
        )
        for index in range(MAX_REGISTERED_BACKENDS + 1)
    )

    with pytest.raises(BackendRegistryError, match="too many"):
        BackendRegistry.from_capabilities(capabilities)


def test_registry_does_not_scan_directories(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifest-dir.json"
    manifest_dir.mkdir()

    with pytest.raises(ManifestError, match="regular file"):
        BackendRegistry.from_manifest_paths([manifest_dir])


def test_registry_filters_supporting_operations_without_lowering() -> None:
    registry = BackendRegistry.from_capabilities(
        [
            BackendCapability(
                name="linear-sim",
                supported_ops=frozenset({OperationKind.MATMUL}),
            ),
            BackendCapability(
                name="vector-sim",
                supported_ops=frozenset({OperationKind.ELEMENTWISE}),
            ),
        ]
    )
    operation = _matmul_graph().operations[0]

    assert registry.supporting_operation_kind(OperationKind.MATMUL)[0].name == "linear-sim"
    assert registry.supporting_operation(operation)[0].name == "linear-sim"


def test_registry_explains_operation_support_decisions() -> None:
    registry = BackendRegistry.from_capabilities(
        [
            BackendCapability(
                name="linear-sim",
                supported_ops=frozenset({OperationKind.MATMUL}),
            ),
            BackendCapability(
                name="vector-sim",
                supported_ops=frozenset({OperationKind.ELEMENTWISE}),
            ),
        ]
    )

    diagnostics = registry.diagnose_operation_support(_matmul_graph().operations[0])

    assert [(item.backend_name, item.supported, item.reason) for item in diagnostics] == [
        ("linear-sim", True, "accepted"),
        ("vector-sim", False, "unsupported_operation_kind"),
    ]


def test_registry_explains_unsupported_layout() -> None:
    registry = BackendRegistry.from_capabilities(
        [
            BackendCapability(
                name="row-only",
                supported_ops=frozenset({OperationKind.MATMUL}),
            )
        ]
    )
    operation = _matmul_graph().operations[0]
    blocked_operation = ComputeOperation(
        name=operation.name,
        kind=operation.kind,
        inputs=operation.inputs,
        outputs=operation.outputs,
        attributes={"tuc.layout": "blocked"},
    )

    diagnostics = registry.diagnose_operation_support(blocked_operation)

    assert diagnostics[0].supported is False
    assert diagnostics[0].reason == "unsupported_layout"
    assert registry.supporting_operation(blocked_operation) == ()


def test_registry_explains_invalid_error_budget() -> None:
    registry = BackendRegistry.from_capabilities(
        [
            BackendCapability(
                name="bounded",
                supported_ops=frozenset({OperationKind.MATMUL}),
                max_error_budget=0.1,
            )
        ]
    )
    operation = _matmul_graph().operations[0]
    invalid_budget_operation = ComputeOperation(
        name=operation.name,
        kind=operation.kind,
        inputs=operation.inputs,
        outputs=operation.outputs,
        attributes={"max_error_budget": -1.0},
    )

    diagnostics = registry.diagnose_operation_support(invalid_budget_operation)

    assert diagnostics[0].supported is False
    assert diagnostics[0].reason == "invalid_error_budget_attribute"
    assert registry.supporting_operation(invalid_budget_operation) == ()


def test_registry_explains_excessive_error_budget() -> None:
    registry = BackendRegistry.from_capabilities(
        [
            BackendCapability(
                name="bounded",
                supported_ops=frozenset({OperationKind.MATMUL}),
                max_error_budget=0.1,
            )
        ]
    )
    operation = _matmul_graph().operations[0]
    excessive_budget_operation = ComputeOperation(
        name=operation.name,
        kind=operation.kind,
        inputs=operation.inputs,
        outputs=operation.outputs,
        attributes={"max_error_budget": 0.2},
    )

    diagnostics = registry.diagnose_operation_support(excessive_budget_operation)

    assert diagnostics[0].supported is False
    assert diagnostics[0].reason == "error_budget_exceeds_backend_limit"
    assert "requested=0.2" in diagnostics[0].detail


def test_manifest_rejects_backend_name_without_alphanumeric_prefix(
    tmp_path: Path,
) -> None:
    path = _write_backend_manifest(tmp_path / "bad.json", name=".hidden")

    with pytest.raises(ManifestError, match="simple string"):
        BackendRegistry.from_manifest_paths([path])


def _write_backend_manifest(path: Path, *, name: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": BACKEND_CAPABILITY_SCHEMA_VERSION,
                "name": name,
                "supported_ops": ["matmul"],
            }
        ),
        encoding="utf-8",
    )
    return path


def _matmul_graph() -> ComputeGraph:
    lhs = TensorRef("lhs", (4, 8))
    rhs = TensorRef("rhs", (8, 2))
    out = TensorRef("out", (4, 2))
    return ComputeGraph(
        name="registry_demo",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(out,),
            ),
        ),
    )
