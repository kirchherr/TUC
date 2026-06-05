from __future__ import annotations

from pathlib import Path

_SPIKE = Path(__file__).parents[1] / "examples" / "mlir" / "tuc_hac_ir_spike.mlir"


def test_mlir_design_spike_contains_hac_ir_contract_markers() -> None:
    text = _SPIKE.read_text(encoding="utf-8")

    assert 'tuc.dialect = "tuc_hac.v0"' in text
    assert 'tuc.stage = "hac-ir"' in text
    assert '"tuc_hac.matmul"' in text
    assert '"tuc_hac.elementwise"' in text
    assert "tuc.bytes_read" in text
    assert "tuc.bytes_written" in text
    assert "tuc.preferred_memory_domain" in text
    assert "tuc.max_error_budget" in text


def test_mlir_design_spike_keeps_code_execution_out_of_artifact() -> None:
    text = _SPIKE.read_text(encoding="utf-8").lower()

    forbidden_fragments = (
        "dlopen",
        "exec",
        "import",
        "include",
        "plugin",
        "subprocess",
    )
    assert all(fragment not in text for fragment in forbidden_fragments)
