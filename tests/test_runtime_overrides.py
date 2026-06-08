from __future__ import annotations

import pytest

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.backends.base import BackendCapability
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.memory import MemoryDomainKind
from tuc.runtime import (
    RUNTIME_OVERRIDE_SCHEMA_VERSION,
    RuntimeOverrideError,
    RuntimeOverrideSet,
    partition_graph,
)


def test_runtime_override_requires_accepted_backend_candidate() -> None:
    graph = _matmul_graph()
    override_set = _override_set(
        (
            {
                "operation_name": "projection",
                "action": "require_backend",
                "backend_name": "gpu-matmul",
            },
        )
    )

    result = compile_graph(
        graph,
        [LinearAlgebraSimulatorBackend().capability, _gpu_matmul_backend()],
        runtime_overrides=override_set,
    )

    assert result.partition_plan.backend_for("projection") == "gpu-matmul"
    assert len(result.partition_plan.override_effects) == 1
    assert 'manual_override:require_backend=gpu-matmul' in result.dump_runtime_plan()
    assert 'require_backend="gpu-matmul"' in result.dump_runtime_plan()
    assert 'manual_overrides {' in result.dump_decision_report()


def test_runtime_override_prefers_accepted_backend_candidate() -> None:
    x = TensorRef("x", (4, 4))
    y = TensorRef("y", (4, 4))
    graph = ComputeGraph(
        name="prefer_demo",
        operations=(
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(x,),
                outputs=(y,),
            ),
        ),
    )
    gpu_backend = BackendCapability(
        name="a-gpu",
        supported_ops=frozenset({OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.GPU_HBM,
    )
    sram_backend = BackendCapability(
        name="z-sram",
        supported_ops=frozenset({OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.DEVICE_SRAM,
    )
    override_set = _override_set(
        (
            {
                "operation_name": "activation",
                "action": "prefer_backend",
                "backend_name": "z-sram",
            },
        )
    )

    plan = partition_graph(
        graph,
        [gpu_backend, sram_backend],
        runtime_overrides=override_set,
    )

    assert plan.backend_for("activation") == "z-sram"
    assert plan.assignments[0].reason.startswith("manual_override:prefer_backend=z-sram")


def test_runtime_override_denies_accepted_backend_candidate() -> None:
    graph = _matmul_graph()
    override_set = _override_set(
        (
            {
                "operation_name": "projection",
                "action": "deny_backend",
                "backend_name": "linear-sim",
            },
        )
    )

    plan = partition_graph(
        graph,
        [LinearAlgebraSimulatorBackend().capability, _gpu_matmul_backend()],
        runtime_overrides=override_set,
    )

    assert plan.backend_for("projection") == "gpu-matmul"
    assert plan.override_effects[0].denied_backends == ("linear-sim",)


def test_runtime_override_rejects_unknown_schema_version() -> None:
    with pytest.raises(RuntimeOverrideError, match="unsupported runtime override schema_version"):
        RuntimeOverrideSet.from_manifest(
            {
                "schema_version": "tuc.runtime_overrides.v99",
                "rules": [],
            }
        )


def test_runtime_override_rejects_unknown_fields() -> None:
    with pytest.raises(RuntimeOverrideError, match="unknown fields"):
        RuntimeOverrideSet.from_manifest(
            {
                "schema_version": RUNTIME_OVERRIDE_SCHEMA_VERSION,
                "rules": [],
                "plugin_path": "evil",
            }
        )


def test_runtime_override_rejects_unknown_action() -> None:
    with pytest.raises(RuntimeOverrideError, match="unsupported runtime override action"):
        _override_set(
            (
                {
                    "operation_name": "projection",
                    "action": "glob_backend",
                    "backend_name": "gpu-matmul",
                },
            )
        )


def test_runtime_override_rejects_duplicate_rules() -> None:
    rule = {
        "operation_name": "projection",
        "action": "require_backend",
        "backend_name": "gpu-matmul",
    }

    with pytest.raises(RuntimeOverrideError, match="duplicate rules"):
        _override_set((rule, rule))


def test_runtime_override_rejects_contradictory_rules() -> None:
    with pytest.raises(RuntimeOverrideError, match="contradictory require_backend"):
        _override_set(
            (
                {
                    "operation_name": "projection",
                    "action": "require_backend",
                    "backend_name": "gpu-matmul",
                },
                {
                    "operation_name": "projection",
                    "action": "deny_backend",
                    "backend_name": "gpu-matmul",
                },
            )
        )


def test_runtime_override_rejects_require_and_prefer_for_same_operation() -> None:
    with pytest.raises(RuntimeOverrideError, match="both require_backend and prefer_backend"):
        _override_set(
            (
                {
                    "operation_name": "projection",
                    "action": "require_backend",
                    "backend_name": "gpu-matmul",
                },
                {
                    "operation_name": "projection",
                    "action": "prefer_backend",
                    "backend_name": "gpu-matmul",
                },
            )
        )


def test_runtime_override_rejects_unknown_operation() -> None:
    override_set = _override_set(
        (
            {
                "operation_name": "missing",
                "action": "require_backend",
                "backend_name": "gpu-matmul",
            },
        )
    )

    with pytest.raises(RuntimeOverrideError, match="unknown operation"):
        partition_graph(
            _matmul_graph(),
            [_gpu_matmul_backend()],
            runtime_overrides=override_set,
        )


def test_runtime_override_rejects_unknown_backend() -> None:
    override_set = _override_set(
        (
            {
                "operation_name": "projection",
                "action": "require_backend",
                "backend_name": "missing-backend",
            },
        )
    )

    with pytest.raises(RuntimeOverrideError, match="unknown backend"):
        partition_graph(
            _matmul_graph(),
            [_gpu_matmul_backend()],
            runtime_overrides=override_set,
        )


def test_runtime_override_rejects_unsupported_backend_candidate() -> None:
    override_set = _override_set(
        (
            {
                "operation_name": "projection",
                "action": "require_backend",
                "backend_name": "elementwise-only",
            },
        )
    )
    elementwise_only = BackendCapability(
        name="elementwise-only",
        supported_ops=frozenset({OperationKind.ELEMENTWISE}),
    )

    with pytest.raises(RuntimeOverrideError, match="not an accepted candidate"):
        partition_graph(
            _matmul_graph(),
            [elementwise_only],
            runtime_overrides=override_set,
        )


def test_runtime_override_rejects_denying_every_candidate() -> None:
    override_set = _override_set(
        (
            {
                "operation_name": "projection",
                "action": "deny_backend",
                "backend_name": "gpu-matmul",
            },
        )
    )

    with pytest.raises(RuntimeOverrideError, match="removes every accepted backend candidate"):
        partition_graph(
            _matmul_graph(),
            [_gpu_matmul_backend()],
            runtime_overrides=override_set,
        )


def test_runtime_override_rejects_rule_count_over_budget() -> None:
    rules = tuple(
        {
            "operation_name": f"projection{i}",
            "action": "require_backend",
            "backend_name": "gpu-matmul",
        }
        for i in range(65)
    )

    with pytest.raises(RuntimeOverrideError, match="rule count exceeds limit"):
        _override_set(rules)


def _matmul_graph() -> ComputeGraph:
    lhs = TensorRef("lhs", (4, 4))
    rhs = TensorRef("rhs", (4, 4))
    out = TensorRef("out", (4, 4))
    return ComputeGraph(
        name="manual_override_demo",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(out,),
                attributes={"max_error_budget": 0.01},
            ),
        ),
    )


def _gpu_matmul_backend() -> BackendCapability:
    return BackendCapability(
        name="gpu-matmul",
        supported_ops=frozenset({OperationKind.MATMUL}),
        memory_domain=MemoryDomainKind.GPU_HBM,
    )


def _override_set(rules: tuple[dict[str, str], ...]) -> RuntimeOverrideSet:
    return RuntimeOverrideSet.from_manifest(
        {
            "schema_version": RUNTIME_OVERRIDE_SCHEMA_VERSION,
            "rules": rules,
        }
    )
