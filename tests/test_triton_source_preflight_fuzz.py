from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from tuc.frontend import (
    MAX_TRITON_SOURCE_DIAGNOSTIC_BYTES,
    MAX_TRITON_SOURCE_DIAGNOSTICS,
    TRITON_SOURCE_PREFLIGHT_CONTRACT,
    TritonSourcePreflightReport,
    preflight_triton_source,
)

CORPUS_DIR = Path("tests/corpus/triton_source_preflight")
SEED_SOURCES = tuple(
    path.read_text(encoding="utf-8")
    for path in sorted(CORPUS_DIR.glob("*.tucsrc"))
)


@given(st.binary(max_size=4096))
@settings(max_examples=100, deadline=None)
def test_triton_source_preflight_handles_arbitrary_decoded_bytes(data: bytes) -> None:
    source = data.decode("utf-8", errors="surrogateescape")

    report = preflight_triton_source(source, source_name="fuzz_source")

    _assert_bounded_report(report)


@given(st.lists(st.sampled_from(SEED_SOURCES), min_size=1, max_size=4))
@settings(max_examples=40, deadline=None)
def test_triton_source_preflight_handles_seed_combinations(seeds: list[str]) -> None:
    source = "\n".join(seeds)

    report = preflight_triton_source(source, source_name="seed_combo")

    _assert_bounded_report(report)


def test_triton_source_preflight_seed_corpus_preserves_expected_decisions() -> None:
    cases = {
        "accepted_matmul_elementwise.tucsrc": (True, ()),
        "import_escape.tucsrc": (False, ("import_statement",)),
        "decorator_call.tucsrc": (False, ("decorator_call",)),
        "host_path_literal.tucsrc": (False, ("host_path_literal",)),
        "hac_ir_leak.tucsrc": (False, ("hac_ir_neutrality_leak",)),
        "unsupported_tl_call.tucsrc": (False, ("unsupported_call_target",)),
    }

    for filename, (accepted, expected_features) in cases.items():
        report = preflight_triton_source(
            (CORPUS_DIR / filename).read_text(encoding="utf-8"),
            source_name=Path(filename).stem,
        )

        assert report.accepted is accepted
        for feature in expected_features:
            assert feature in report.rejected_features
        _assert_bounded_report(report)


def test_triton_source_preflight_rejects_invalid_unicode_without_crashing() -> None:
    source = b"\xff\xfe@triton.jit\n".decode("utf-8", errors="surrogateescape")

    report = preflight_triton_source(source, source_name="invalid_unicode")

    assert report.accepted is False
    assert "invalid_unicode" in report.rejected_features
    _assert_bounded_report(report)


def test_triton_source_preflight_caps_diagnostic_volume() -> None:
    source = "\n".join("import os" for _ in range(MAX_TRITON_SOURCE_DIAGNOSTICS + 50))
    source = f"{source}\n@triton.jit\ndef kernel(a):\n    return a\n"

    report = preflight_triton_source(source, source_name="many_imports")

    assert report.accepted is False
    assert "import_statement" in report.rejected_features
    assert len(report.diagnostics) <= MAX_TRITON_SOURCE_DIAGNOSTICS
    assert (
        sum(len(diagnostic.encode("utf-8")) for diagnostic in report.diagnostics)
        <= MAX_TRITON_SOURCE_DIAGNOSTIC_BYTES
    )


def _assert_bounded_report(report: TritonSourcePreflightReport) -> None:
    assert report.intake_contract == TRITON_SOURCE_PREFLIGHT_CONTRACT
    assert isinstance(report.accepted, bool)
    assert report.source_bytes >= 0
    assert report.line_count >= 0
    assert report.ast_node_count >= 0
    assert report.ast_depth >= 0
    assert report.identifier_count >= 0
    assert report.literal_count >= 0
    assert len(report.diagnostics) <= MAX_TRITON_SOURCE_DIAGNOSTICS
    assert (
        sum(len(diagnostic.encode("utf-8")) for diagnostic in report.diagnostics)
        <= MAX_TRITON_SOURCE_DIAGNOSTIC_BYTES
    )
    assert "python_import" in report.blocked_execution_surfaces
    assert "decorator_evaluation" in report.blocked_execution_surfaces
    assert "jit_execution" in report.blocked_execution_surfaces
    assert "ComputeGraph" not in report.dump()
