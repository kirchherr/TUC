from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.runtime_evidence_replay_verifier import (
    build_evidence_replay_verifier_report,
    build_report,
)
from examples.runtime_execution_evidence_bundle import (
    build_execution_evidence_bundle_report,
)
from examples.runtime_execution_output_closure import (
    build_execution_output_closure_report,
)
from tuc.runtime.evidence_replay_verifier import (
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECK_STATUS,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION,
    assert_runtime_evidence_replay_verifier,
    build_runtime_evidence_replay_verifier_report,
)
from tuc.runtime.execution_evidence_bundle import (
    dump_runtime_execution_evidence_bundle_report,
)
from tuc.runtime.execution_output_closure import (
    dump_runtime_execution_output_closure_report,
)

GOLDEN_PATH = Path("tests/golden/runtime_evidence_replay_verifier/proof_of_execution.json")
SCHEMA_PATH = Path("schemas/runtime_evidence_replay_verifier_report.v0.schema.json")


def test_runtime_evidence_replay_verifier_passes_for_execution_proof() -> None:
    report = build_evidence_replay_verifier_report()

    assert report.replay_contract == RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT
    assert report.replay_mode == RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE
    assert report.input_policy == RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY
    assert report.reexecution_policy == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY
    )
    assert report.graph_name == "proof_of_execution"
    assert report.passed
    assert report.issues == ()
    assert report.check_count == 8
    assert {check.row_status for check in report.checks} == {
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECK_STATUS
    }
    assert tuple(check.check_id for check in report.checks) == (
        "graph_name_match",
        "evidence_bundle_metadata_digest_replayed",
        "execution_receipt_metadata_digest_replayed",
        "output_closure_metadata_digest_replayed",
        "closure_binds_evidence_bundle",
        "closure_binds_execution_receipt",
        "closure_binds_output_contract",
        "closure_binds_public_output_bundle",
    )


def test_runtime_evidence_replay_verifier_dump_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_runtime_evidence_replay_verifier_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_evidence_replay_verifier.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT in completed.stdout
    assert "metadata_digest_replay_only" in completed.stdout
    assert "runtime_reexecution_not_required" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "tensor_values" not in completed.stdout


def test_runtime_evidence_replay_verifier_assertion_returns_report() -> None:
    report = build_evidence_replay_verifier_report()

    assert assert_runtime_evidence_replay_verifier(report) is report


def test_runtime_evidence_replay_verifier_detects_forged_closure_link() -> None:
    evidence_bundle_text = dump_runtime_execution_evidence_bundle_report(
        build_execution_evidence_bundle_report()
    )
    output_closure = json.loads(
        dump_runtime_execution_output_closure_report(
            build_execution_output_closure_report()
        )
    )
    output_closure["source_output_contract_metadata_digest"] = (
        "sha256:" + "1" * 64
    )
    output_closure_text = json.dumps(output_closure, indent=2, sort_keys=True) + "\n"

    report = build_runtime_evidence_replay_verifier_report(
        evidence_bundle_text,
        output_closure_text,
    )

    assert not report.passed
    assert {issue.issue_code for issue in report.issues} == {
        "output_closure_metadata_digest_replayed_mismatch",
        "closure_binds_output_contract_mismatch",
    }
    with pytest.raises(AssertionError, match="closure_binds_output_contract"):
        assert_runtime_evidence_replay_verifier(report)


def test_runtime_evidence_replay_verifier_rejects_source_or_raw_values() -> None:
    evidence_bundle_text = dump_runtime_execution_evidence_bundle_report(
        build_execution_evidence_bundle_report()
    )
    output_closure_text = dump_runtime_execution_output_closure_report(
        build_execution_output_closure_report()
    )

    with pytest.raises(ValueError, match="forbidden replay verifier fragment"):
        build_runtime_evidence_replay_verifier_report(
            evidence_bundle_text + '{"python_source": "@triton.jit"}',
            output_closure_text,
        )


def test_runtime_evidence_replay_verifier_rejects_non_json_report() -> None:
    output_closure_text = dump_runtime_execution_output_closure_report(
        build_execution_output_closure_report()
    )

    with pytest.raises(ValueError, match="valid JSON"):
        build_runtime_evidence_replay_verifier_report(
            "not json",
            output_closure_text,
        )


def test_runtime_evidence_replay_verifier_schema_matches_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["replay_contract"]["const"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT
    )
    assert schema["properties"]["replay_mode"]["const"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE
    )
    assert schema["properties"]["input_policy"]["const"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY
    )
    assert schema["properties"]["reexecution_policy"]["const"] == (
        RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY
    )
    assert schema["properties"]["check_count"]["const"] == 8
    assert schema["$defs"]["check"]["additionalProperties"] is False


def test_runtime_evidence_replay_verifier_is_documented_and_in_ci() -> None:
    example_path = "examples/runtime_evidence_replay_verifier.py"
    doc_path = "RUNTIME_EVIDENCE_REPLAY_VERIFIER.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/RUNTIME_EVIDENCE_FLOW.md"),
        Path("docs/RUNTIME_EVIDENCE_GATE.md"),
        Path("docs/RUNTIME_EXECUTION_EVIDENCE_BUNDLE.md"),
        Path("docs/RUNTIME_EXECUTION_OUTPUT_CLOSURE.md"),
        Path("docs/RUNTIME_EVIDENCE_REPLAY_VERIFIER.md"),
        Path("rfcs/0210-runtime-evidence-replay-verifier.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/RUNTIME_EVIDENCE_FLOW.md"),
        Path("rfcs/0210-runtime-evidence-replay-verifier.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
