from __future__ import annotations

import pytest

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime import (
    LayoutConversionCost,
    RuntimeTransferEdge,
    TransferCostEstimate,
    TransferCostProfile,
    estimate_default_transfer_cost,
)


def test_runtime_transfer_edge_rejects_same_domain_transfer() -> None:
    with pytest.raises(ValueError, match="domains must differ"):
        RuntimeTransferEdge(
            tensor_name="x",
            source_operation="producer",
            target_operation="consumer",
            source_backend="gpu",
            target_backend="gpu",
            source_domain=MemoryDomainKind.GPU_HBM,
            target_domain=MemoryDomainKind.GPU_HBM,
            source_layout=LayoutKind.ROW_MAJOR,
            target_layout=LayoutKind.ROW_MAJOR,
            bytes_moved=1024,
        )


def test_runtime_transfer_edge_rejects_zero_bytes() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        RuntimeTransferEdge(
            tensor_name="x",
            source_operation="producer",
            target_operation="consumer",
            source_backend="gpu",
            target_backend="linear-sim",
            source_domain=MemoryDomainKind.GPU_HBM,
            target_domain=MemoryDomainKind.ANALOG_WEIGHT_BANK,
            source_layout=LayoutKind.ROW_MAJOR,
            target_layout=LayoutKind.ROW_MAJOR,
            bytes_moved=0,
        )


def test_runtime_transfer_edge_adds_default_cost_estimate() -> None:
    edge = RuntimeTransferEdge(
        tensor_name="x",
        source_operation="producer",
        target_operation="consumer",
        source_backend="linear-sim",
        target_backend="gpu",
        source_domain=MemoryDomainKind.ANALOG_WEIGHT_BANK,
        target_domain=MemoryDomainKind.GPU_HBM,
        source_layout=LayoutKind.ROW_MAJOR,
        target_layout=LayoutKind.ROW_MAJOR,
        bytes_moved=1024,
    )

    assert edge.cost_estimate is not None
    assert edge.cost_estimate.bandwidth_gb_s == 64.0
    assert edge.cost_estimate.estimated_latency_ns == pytest.approx(5016.0)
    assert edge.cost_estimate.estimated_energy_pj == pytest.approx(20480.0)


def test_transfer_cost_estimate_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        TransferCostEstimate(
            bytes_moved=1024,
            bandwidth_gb_s=float("nan"),
            base_latency_ns=1.0,
            energy_pj_per_byte=1.0,
        )


def test_default_transfer_cost_rejects_same_domain() -> None:
    with pytest.raises(ValueError, match="different domains"):
        estimate_default_transfer_cost(
            bytes_moved=1024,
            source_domain=MemoryDomainKind.GPU_HBM,
            target_domain=MemoryDomainKind.GPU_HBM,
        )


def test_transfer_cost_profile_from_manifest_estimates_known_edge() -> None:
    profile = TransferCostProfile.from_manifest(
        {
            "name": "calibrated_v0",
            "fallback": {
                "bandwidth_gb_s": 10.0,
                "base_latency_ns": 1000.0,
                "energy_pj_per_byte": 5.0,
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

    estimate = profile.estimate(
        bytes_moved=1024,
        source_domain=MemoryDomainKind.ANALOG_WEIGHT_BANK,
        target_domain=MemoryDomainKind.GPU_HBM,
    )

    assert estimate.estimated_latency_ns == pytest.approx(2508.0)
    assert estimate.estimated_energy_pj == pytest.approx(12288.0)


def test_transfer_cost_profile_manifest_rejects_duplicate_edges() -> None:
    manifest = {
        "name": "bad",
        "fallback": {
            "bandwidth_gb_s": 10.0,
            "base_latency_ns": 1000.0,
            "energy_pj_per_byte": 5.0,
        },
        "edges": (
            {
                "source_domain": "gpu_hbm",
                "target_domain": "host_ram",
                "bandwidth_gb_s": 10.0,
                "base_latency_ns": 1000.0,
                "energy_pj_per_byte": 5.0,
            },
            {
                "source_domain": "gpu_hbm",
                "target_domain": "host_ram",
                "bandwidth_gb_s": 20.0,
                "base_latency_ns": 1000.0,
                "energy_pj_per_byte": 5.0,
            },
        ),
    }

    with pytest.raises(ValueError, match="duplicate domain pair"):
        TransferCostProfile.from_manifest(manifest)


def test_transfer_cost_profile_manifest_rejects_custom_mapping() -> None:
    class CustomManifest(dict[str, object]):
        pass

    manifest = CustomManifest(
        {
            "name": "custom",
            "fallback": {
                "bandwidth_gb_s": 1,
                "base_latency_ns": 0,
                "energy_pj_per_byte": 0,
            },
        }
    )

    with pytest.raises(TypeError, match="plain mapping"):
        TransferCostProfile.from_manifest(manifest)


def test_layout_conversion_rejects_noop_conversion() -> None:
    with pytest.raises(ValueError, match="different layouts"):
        LayoutConversionCost(
            tensor_name="x",
            source_operation="producer",
            target_operation="consumer",
            source_layout=LayoutKind.ROW_MAJOR,
            target_layout=LayoutKind.ROW_MAJOR,
            bytes_converted=1024,
            reason="layout_mismatch",
        )
