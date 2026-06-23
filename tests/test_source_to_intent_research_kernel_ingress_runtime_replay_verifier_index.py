from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_runtime_replay_verifier_index import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_runtime_replay_verifier_index_report_contract,
    build_kernel_ingress_runtime_replay_verifier_index_report,
    build_report,
)
from tuc.runtime import (
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/"
    "source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.json"
)
SCHEMA_PATH = Path(
    "schemas/"
    "source_to_intent_research_kernel_ingress_runtime_replay_verifier_index_report.v0.schema.json"
)


def test_kernel_ingress_runtime_replay_verifier_index_report_shape() -> None:
    report = build_kernel_ingress_runtime_replay_verifier_index_report()
    assert_kernel_ingress_runtime_replay_verifier_index_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_REPORT_SCHEMA_VERSION
    )
    assert report["replay_verifier_index_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_CONTRACT
    )
    assert report["replay_verifier_schema_version"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION
    )
    assert report["replay_verifier_contract"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT
    )
    assert report["replay_verifier_replay_mode"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE
    )
    assert report["input_policy"] == RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY
    assert report["reexecution_policy"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY
    )
    assert report["status"] == "PASS"
    assert report["case_count"] == 4
    mvp_case = report["cases"][3]
    assert mvp_case["case_id"] == "research_module_mvp_pipeline"
    assert mvp_case["graph_name"] == "research_mvp_pipeline"
    assert mvp_case["operation_path"] == [
        "matmul",
        "softmax",
        "reduction",
        "elementwise",
    ]
    assert mvp_case["passed"] is True
    assert mvp_case["step_count"] == 4
    assert mvp_case["replay_check_count"] == 8
    assert mvp_case["raw_value_policy"] == "omitted_by_policy"


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("case_count", 3, "case_count"),
        ("replay_verifier_contract", "other", "replay_verifier_contract"),
        ("raw_source", "@triton.jit", "top-level report"),
    ],
)
def test_kernel_ingress_runtime_replay_verifier_index_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_runtime_replay_verifier_index_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_runtime_replay_verifier_index_report_contract(report)


def test_kernel_ingress_runtime_replay_verifier_index_rejects_case_drift() -> None:
    report = build_kernel_ingress_runtime_replay_verifier_index_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[3], dict)
    cases[3]["replay_check_count"] = 7

    with pytest.raises(ValueError, match="replay_check_count drift"):
        assert_kernel_ingress_runtime_replay_verifier_index_report_contract(report)


def test_kernel_ingress_runtime_replay_verifier_index_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_runtime_replay_verifier_index_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            (
                "examples/"
                "source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"replay_verifier_contract"' in completed.stdout
    assert '"replay_report_digest"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_kernel_ingress_runtime_replay_verifier_index_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["replay_verifier_index_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_CONTRACT
    )
    assert schema["properties"]["replay_verifier_contract"]["const"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT
    )
    assert schema["properties"]["replay_verifier_schema_version"]["const"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["replay_verifier_replay_mode"]["const"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "output_closure_index_digest" in schema["required"]


def test_kernel_ingress_runtime_replay_verifier_index_is_documented_and_in_ci() -> None:
    example_path = (
        "examples/"
        "source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py"
    )
    doc_path = (
        "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX.md"
    )

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md"),
        Path("rfcs/0178-source-to-intent-research-capability-claim.md"),
        Path(
            "rfcs/"
            "0209-source-to-intent-research-kernel-ingress-runtime-output-closure-index.md"
        ),
        Path(
            "rfcs/"
            "0211-source-to-intent-research-kernel-ingress-runtime-replay-verifier-index.md"
        ),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path(
            "rfcs/"
            "0211-source-to-intent-research-kernel-ingress-runtime-replay-verifier-index.md"
        ),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
