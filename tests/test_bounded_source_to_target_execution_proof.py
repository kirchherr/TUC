from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import cast

import pytest

from examples import bounded_source_to_target_execution_proof as proof
from examples import oci_source_ingestion_research_proof as oci_proof
from examples.bounded_compiler_emission import _digest_payload
from examples.bounded_source_to_target_execution_proof import (
    BoundedSourceToTargetExecutionProofError,
    assert_bounded_source_to_target_execution_proof,
    build_bounded_source_to_target_execution_proof,
    dump_bounded_source_to_target_execution_proof,
)

DOC_PATH = Path("docs/BOUNDED_SOURCE_TO_TARGET_EXECUTION_PROOF.md")
RFC_PATH = Path("rfcs/0304-bounded-source-to-target-execution-proof.md")
WORKFLOW_PATH = Path(".github/workflows/bounded-c11-proof.yml")


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert type(payload) is dict
    return cast(dict[str, object], payload)


def _children() -> tuple[dict[str, object], dict[str, object]]:
    return _load(proof.OCI_GOLDEN_PATH), _load(
        proof.TARGET_EQUIVALENCE_GOLDEN_PATH
    )


def _recompute_digest(report: dict[str, object]) -> None:
    payload = dict(report)
    payload.pop("report_digest", None)
    report["report_digest"] = _digest_payload(payload)


def test_source_to_target_proof_matches_closed_schema_and_golden() -> None:
    frontend, target = _children()
    report = build_bounded_source_to_target_execution_proof(frontend, target)
    rendered = dump_bounded_source_to_target_execution_proof(report)
    schema = _load(proof.SCHEMA_PATH)
    properties = cast(dict[str, object], schema["properties"])

    assert rendered == proof.GOLDEN_PATH.read_text(encoding="utf-8")
    for key, value in report.items():
        property_schema = cast(dict[str, object], properties[key])
        if key == "report_digest":
            assert property_schema["pattern"] == "^sha256:[0-9a-f]{64}$"
        else:
            assert property_schema["const"] == value
    assert schema["additionalProperties"] is False
    assert sorted(cast(list[str], schema["required"])) == sorted(report)


def test_source_to_target_proof_binds_one_inert_source_to_two_targets() -> None:
    frontend, target = _children()
    report = build_bounded_source_to_target_execution_proof(frontend, target)
    binding = cast(dict[str, object], report["binding"])
    boundary = cast(dict[str, object], report["claim_boundary"])
    frontend_summary = cast(dict[str, object], report["frontend"])
    target_summary = cast(dict[str, object], report["target_execution"])

    assert binding["source_text_executed"] is False
    assert binding["source_intent_digest_equal"] is True
    assert binding["terminal_reference_semantics_preserved"] is True
    assert boundary["source_case_count"] == 1
    assert boundary["compiler_target_count"] == 2
    assert boundary["default_source_ingestion_admitted"] is False
    assert frontend_summary["source_intent_digest"] == target_summary[
        "source_intent_digest"
    ]
    assert target_summary["target_families"] == [
        "cuda_sass_sm86",
        "c11_static_elf_x86_64",
    ]


@pytest.mark.parametrize(
    "field",
    (
        "compose_contract_digest",
        "dockerfile_digest",
        "rejection_request_digest",
        "requirements_digest",
        "source_intent_digest",
        "vertical_proof_digest",
        "worker_request_digest",
        "worker_source_digest",
    ),
)
def test_oci_child_validator_rejects_recomputed_provenance_drift(
    field: str,
) -> None:
    frontend = _load(proof.OCI_GOLDEN_PATH)
    frontend[field] = "sha256:" + "0" * 64
    payload = dict(frontend)
    payload.pop("report_digest")
    frontend["report_digest"] = oci_proof._digest_payload(payload)

    with pytest.raises(ValueError, match=f"{field} provenance drift"):
        oci_proof.assert_oci_source_ingestion_research_proof_report(frontend)


def test_source_to_target_builder_rejects_frontend_child_drift() -> None:
    frontend, target = _children()
    frontend["worker_request_digest"] = "sha256:" + "0" * 64
    payload = dict(frontend)
    payload.pop("report_digest")
    frontend["report_digest"] = oci_proof._digest_payload(payload)

    with pytest.raises(
        BoundedSourceToTargetExecutionProofError,
        match="child evidence rejected",
    ):
        build_bounded_source_to_target_execution_proof(frontend, target)


def test_source_to_target_builder_rejects_target_child_drift() -> None:
    frontend, target = _children()
    source_intent = cast(dict[str, object], target["source_intent"])
    source_intent["payload_digest"] = "sha256:" + "0" * 64
    _recompute_digest(target)

    with pytest.raises(
        BoundedSourceToTargetExecutionProofError,
        match="child evidence rejected",
    ):
        build_bounded_source_to_target_execution_proof(frontend, target)


def test_source_to_target_validator_rejects_claim_promotion() -> None:
    frontend, target = _children()
    report = build_bounded_source_to_target_execution_proof(frontend, target)
    boundary = cast(dict[str, object], report["claim_boundary"])
    boundary["universal_compute_claim_proven"] = True
    boundary["default_source_ingestion_admitted"] = True
    _recompute_digest(report)

    with pytest.raises(
        BoundedSourceToTargetExecutionProofError,
        match="invariant drift",
    ):
        assert_bounded_source_to_target_execution_proof(report)


def test_source_to_target_validator_and_schema_reject_extra_fields() -> None:
    frontend, target = _children()
    report = build_bounded_source_to_target_execution_proof(frontend, target)
    changed = copy.deepcopy(report)
    changed["host_path"] = "/should/not/pass"
    schema = _load(proof.SCHEMA_PATH)

    with pytest.raises(
        BoundedSourceToTargetExecutionProofError,
        match="key drift",
    ):
        assert_bounded_source_to_target_execution_proof(changed)
    assert schema["additionalProperties"] is False
    assert "host_path" not in cast(dict[str, object], schema["properties"])


def test_source_to_target_loader_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"proof":{},"proof":{}}', encoding="utf-8")

    with pytest.raises(
        BoundedSourceToTargetExecutionProofError,
        match="JSON rejected",
    ):
        proof._load_report(duplicate, "duplicate report")


def test_public_report_is_metadata_only() -> None:
    frontend, target = _children()
    rendered = dump_bounded_source_to_target_execution_proof(
        build_bounded_source_to_target_execution_proof(frontend, target)
    )

    for forbidden in (
        "@triton.jit",
        "import triton",
        '"command"',
        '"generated_source"',
        '"module_source"',
        '"raw_tensor_values"',
        '"source_intent_payload"',
        "C:\\Users\\",
        "/home/",
    ):
        assert forbidden not in rendered


def test_docs_preserve_scope_and_reference_every_public_artifact() -> None:
    combined = DOC_PATH.read_text(encoding="utf-8") + RFC_PATH.read_text(
        encoding="utf-8"
    )

    for path in (
        proof.SCHEMA_PATH,
        proof.GOLDEN_PATH,
        proof.OCI_GOLDEN_PATH,
        proof.TARGET_EQUIVALENCE_GOLDEN_PATH,
    ):
        assert path.relative_to(proof.REPOSITORY_ROOT).as_posix() in combined
    assert "not a live monolithic pipeline run" in combined.lower()
    assert "independent reproduction" in combined
    assert "arbitrary Triton" in combined
    assert "dev001" not in combined
    assert "dev002" not in combined
    assert "192.168." not in combined
    assert "id_ed25519" not in combined


def test_read_only_workflow_verifies_source_to_target_aggregate() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "permissions:\n  contents: read\n" in workflow
    assert "pull_request_target" not in workflow
    assert "secrets." not in workflow
    assert "@v" not in workflow
    assert (
        "python examples/bounded_source_to_target_execution_proof.py" in workflow
    )
