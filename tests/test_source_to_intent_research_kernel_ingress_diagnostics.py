from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_diagnostics import (
    build_source_to_intent_research_kernel_ingress_diagnostic_cases,
)
from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SourceToIntentResearchKernelIngressDiagnosticCase,
    SourceToIntentResearchKernelIngressDiagnosticResult,
    SourceToIntentResearchKernelIngressDiagnosticsReport,
    build_source_to_intent_research_kernel_ingress_diagnostics_report,
    dump_source_to_intent_research_kernel_ingress_diagnostics_report,
    source_to_intent_research_kernel_ingress_diagnostics_report_to_dict,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/"
    "source_to_intent_research_kernel_ingress_diagnostics_report.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_kernel_ingress_diagnostics_report.v0.schema.json"
)


def test_kernel_ingress_diagnostics_tracks_accepted_and_rejected_cases() -> None:
    report = build_source_to_intent_research_kernel_ingress_diagnostics_report(
        build_source_to_intent_research_kernel_ingress_diagnostic_cases()
    )

    assert report.diagnostics_contract == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
    )
    assert report.ingress_contract == SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT
    assert report.raw_source_policy == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY
    )
    assert report.raw_value_policy == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY
    )
    assert report.accepted_case_count == 4
    assert report.rejected_case_count == 5
    assert report.rejection_reasons == tuple(
        sorted(SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS)
    )
    assert tuple(case.case_id for case in report.cases) == (
        "accepted_module_matmul_elementwise",
        "accepted_module_softmax_reduction",
        "accepted_module_matmul_reduction",
        "accepted_module_mvp_pipeline",
        "reject_unsupported_import",
        "reject_import_from_statement",
        "reject_multiple_kernel_functions",
        "reject_top_level_side_effect",
        "reject_kernel_name_mismatch",
    )


def test_kernel_ingress_diagnostics_dump_matches_golden() -> None:
    report = build_source_to_intent_research_kernel_ingress_diagnostics_report(
        build_source_to_intent_research_kernel_ingress_diagnostic_cases()
    )

    assert dump_source_to_intent_research_kernel_ingress_diagnostics_report(
        report
    ) == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_diagnostics_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_diagnostics.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"raw_source_policy": "omitted_by_policy"' in completed.stdout
    assert '"unsupported_import"' in completed.stdout
    assert '"kernel_name_mismatch"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "secret.txt" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_kernel_ingress_diagnostics_omits_source_and_compiler_artifacts() -> None:
    payload = source_to_intent_research_kernel_ingress_diagnostics_report_to_dict(
        build_source_to_intent_research_kernel_ingress_diagnostics_report(
            build_source_to_intent_research_kernel_ingress_diagnostic_cases()
        )
    )
    encoded = str(payload)

    assert payload["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_SCHEMA_VERSION
    )
    assert "module_source" not in payload["cases"][0]
    assert "@triton.jit" not in encoded
    assert "import triton" not in encoded
    assert "tl.store" not in encoded
    assert "secret.txt" not in encoded
    assert "source_intent_payload" not in encoded
    assert "compute_graph" in payload["blocked_compiler_outputs"]


def test_kernel_ingress_diagnostics_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["diagnostics_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
    )
    assert schema["properties"]["ingress_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT
    )
    assert set(
        item["const"] for item in schema["properties"]["rejection_reasons"]["prefixItems"]
    ) == set(SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS)
    assert schema["$defs"]["case"]["additionalProperties"] is False


def test_kernel_ingress_diagnostics_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_kernel_ingress_diagnostics.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
        Path("rfcs/0166-source-to-intent-research-kernel-ingress-diagnostics.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0166-source-to-intent-research-kernel-ingress-diagnostics.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")


def test_kernel_ingress_diagnostics_rejects_unexpected_acceptance() -> None:
    accepted = build_source_to_intent_research_kernel_ingress_diagnostic_cases()[0]
    tampered = SourceToIntentResearchKernelIngressDiagnosticCase(
        case_id="accepted_marked_rejected",
        expectation="rejected",
        module_source=accepted.module_source,
        source_name=accepted.source_name,
        kernel_name=accepted.kernel_name,
        tensor_shapes=accepted.tensor_shapes,
        expected_rejection_reason="unsupported_import",
    )

    with pytest.raises(ValueError, match="unexpectedly accepted"):
        build_source_to_intent_research_kernel_ingress_diagnostics_report((tampered,))


def test_kernel_ingress_diagnostics_rejects_reason_mismatch() -> None:
    rejected = build_source_to_intent_research_kernel_ingress_diagnostic_cases()[4]
    tampered = replace(
        rejected,
        expected_rejection_reason="kernel_name_mismatch",
    )

    with pytest.raises(ValueError, match="reason mismatch"):
        build_source_to_intent_research_kernel_ingress_diagnostics_report((tampered,))


def test_kernel_ingress_diagnostics_report_rejects_malformed_cases() -> None:
    accepted = build_source_to_intent_research_kernel_ingress_diagnostics_report(
        build_source_to_intent_research_kernel_ingress_diagnostic_cases()
    ).cases[0]

    with pytest.raises(ValueError, match="must not reject"):
        SourceToIntentResearchKernelIngressDiagnosticResult(
            case_id="bad_accepted",
            expectation="accepted",
            outcome="accepted",
            source_name="bad_accepted",
            kernel_name="bad_kernel",
            module_bytes=1,
            module_digest="sha256:" + ("0" * 64),
            ingress_report_digest="sha256:" + ("1" * 64),
            rejection_reason="unsupported_import",
        )
    with pytest.raises(ValueError, match="case IDs must be unique"):
        SourceToIntentResearchKernelIngressDiagnosticsReport(cases=(accepted, accepted))
