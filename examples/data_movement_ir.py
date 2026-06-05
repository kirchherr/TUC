"""Inspect data-movement metadata carried from HAC-IR into HS-IR."""

from __future__ import annotations

from tuc import CompilationHints, ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.runtime import TransferCostProfile


def build_graph() -> ComputeGraph:
    hints = CompilationHints(
        prefer_analog_linear=True,
        max_error_budget=0.02,
    )
    a = TensorRef("a", (64, 128))
    b = TensorRef("b", (128, 32))
    c = TensorRef("c", (64, 32))
    y = TensorRef("y", (64, 32))

    return ComputeGraph(
        name="movement_aware_mlp",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes=hints.to_metadata(),
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(c,),
                outputs=(y,),
            ),
        ),
    )


def main() -> None:
    transfer_profile = TransferCostProfile.from_manifest(
        {
            "name": "example_profile",
            "fallback": {
                "bandwidth_gb_s": 16.0,
                "base_latency_ns": 20000.0,
                "energy_pj_per_byte": 100.0,
            },
            "edges": (
                {
                    "source_domain": "analog_weight_bank",
                    "target_domain": "gpu_hbm",
                    "bandwidth_gb_s": 128.0,
                    "base_latency_ns": 2500.0,
                    "energy_pj_per_byte": 12.0,
                },
            ),
        }
    )
    result = compile_graph(
        build_graph(),
        [LinearAlgebraSimulatorBackend().capability],
        transfer_cost_profile=transfer_profile,
    )

    print("== movement summary ==")
    for key, value in sorted(result.hs_ir.graph.metadata["movement_summary"].items()):
        print(f"{key}: {value}")

    print("\n== runtime transfer summary ==")
    for key, value in sorted(result.hs_ir.graph.metadata["runtime_transfer_summary"].items()):
        print(f"{key}: {value}")

    if result.partition_plan.transfer_edges:
        print("\n== runtime transfers ==")
        for edge in result.partition_plan.transfer_edges:
            cost = edge.cost_estimate
            if cost is None:
                raise RuntimeError("runtime transfer is missing a cost estimate")
            print(
                f"%{edge.tensor_name}: {edge.source_backend}/{edge.source_domain.value}"
                f" -> {edge.target_backend}/{edge.target_domain.value}"
                f" ({edge.bytes_moved} bytes, "
                f"{cost.estimated_latency_ns:.3f} ns, "
                f"{cost.estimated_energy_pj:.3f} pJ)"
            )

    print("\n== runtime plan ==")
    print(result.dump_runtime_plan())

    print("\n== hs-ir ==")
    print(result.dump(result.hs_ir.stage))


if __name__ == "__main__":
    main()
