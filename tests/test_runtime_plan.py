from __future__ import annotations

import pytest

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime import LayoutConversionCost, RuntimeTransferEdge


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
