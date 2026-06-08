from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from examples.proof_of_abstraction import run_proof
from examples.proof_of_reduction import run_proof as run_reduction_proof
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.backends.base import BackendCapability
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime import (
    RUNTIME_OVERRIDE_SCHEMA_VERSION,
    PartitionPlan,
    RuntimeOverrideSet,
    TransferCostProfile,
    dump_partition_plan,
    partition_graph,
)

_GOLDEN_DIR = Path(__file__).parent / "golden" / "runtime_plans"


@pytest.mark.parametrize(
    ("fixture_name", "builder"),
    (
        ("default_transfer.txt", lambda: _default_transfer_plan()),
        ("produced_layout_conversion.txt", lambda: _produced_layout_conversion_plan()),
        ("profiled_transfer.txt", lambda: _profiled_transfer_plan()),
        ("manual_override_require.txt", lambda: _manual_override_plan()),
        (
            "proof_of_abstraction.txt",
            lambda: run_proof().compiled.partition_plan,
        ),
        (
            "proof_of_reduction.txt",
            lambda: run_reduction_proof().compiled.partition_plan,
        ),
    ),
)
def test_runtime_plan_dump_matches_golden(
    fixture_name: str,
    builder: Callable[[], PartitionPlan],
) -> None:
    expected = (_GOLDEN_DIR / fixture_name).read_text(encoding="utf-8").rstrip("\n")

    assert dump_partition_plan(builder()) == expected


def _default_transfer_plan() -> PartitionPlan:
    a = TensorRef("a", (16, 16))
    b = TensorRef("b", (16, 16))
    c = TensorRef("c", (16, 16))
    y = TensorRef("y", (16, 16))
    graph = ComputeGraph(
        name="golden_default_transfer",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes={"max_error_budget": 0.01},
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(c,),
                outputs=(y,),
            ),
        ),
    )
    return partition_graph(graph, [LinearAlgebraSimulatorBackend().capability])


def _produced_layout_conversion_plan() -> PartitionPlan:
    x = TensorRef("x", (8, 8))
    y = TensorRef("y", (8, 8))
    z = TensorRef("z", (8, 8))
    graph = ComputeGraph(
        name="golden_produced_layout_conversion",
        operations=(
            ComputeOperation(
                name="first",
                kind=OperationKind.ELEMENTWISE,
                inputs=(x,),
                outputs=(y,),
                attributes={"tuc.layout": LayoutKind.BLOCKED.value},
            ),
            ComputeOperation(
                name="second",
                kind=OperationKind.ELEMENTWISE,
                inputs=(y,),
                outputs=(z,),
                attributes={"tuc.layout": LayoutKind.BLOCKED.value},
            ),
        ),
    )
    backend = BackendCapability(
        name="blocked_in_row_out",
        supported_ops=frozenset({OperationKind.ELEMENTWISE}),
        supported_layouts=frozenset({LayoutKind.BLOCKED}),
        produced_layouts=frozenset({LayoutKind.ROW_MAJOR}),
    )
    return partition_graph(graph, [backend])


def _profiled_transfer_plan() -> PartitionPlan:
    a = TensorRef("a", (8, 8))
    b = TensorRef("b", (8, 8))
    c = TensorRef("c", (8, 8))
    y = TensorRef("y", (8, 8))
    graph = ComputeGraph(
        name="golden_profiled_transfer",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes={"max_error_budget": 0.01},
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(c,),
                outputs=(y,),
            ),
        ),
    )
    profile = TransferCostProfile.from_manifest(
        {
            "name": "golden_profile",
            "fallback": {
                "bandwidth_gb_s": 10.0,
                "base_latency_ns": 1000.0,
                "energy_pj_per_byte": 1.0,
            },
            "edges": (
                {
                    "source_domain": "analog_weight_bank",
                    "target_domain": "gpu_hbm",
                    "bandwidth_gb_s": 256.0,
                    "base_latency_ns": 100.0,
                    "energy_pj_per_byte": 3.0,
                },
            ),
        }
    )
    return partition_graph(
        graph,
        [LinearAlgebraSimulatorBackend().capability],
        transfer_cost_profile=profile,
    )


def _manual_override_plan() -> PartitionPlan:
    lhs = TensorRef("lhs", (4, 4))
    rhs = TensorRef("rhs", (4, 4))
    out = TensorRef("out", (4, 4))
    graph = ComputeGraph(
        name="golden_manual_override",
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
    gpu_backend = BackendCapability(
        name="gpu-matmul",
        supported_ops=frozenset({OperationKind.MATMUL}),
        memory_domain=MemoryDomainKind.GPU_HBM,
    )
    overrides = RuntimeOverrideSet.from_manifest(
        {
            "schema_version": RUNTIME_OVERRIDE_SCHEMA_VERSION,
            "rules": (
                {
                    "operation_name": "projection",
                    "action": "require_backend",
                    "backend_name": "gpu-matmul",
                },
            ),
        }
    )
    return partition_graph(
        graph,
        [LinearAlgebraSimulatorBackend().capability, gpu_backend],
        runtime_overrides=overrides,
    )
