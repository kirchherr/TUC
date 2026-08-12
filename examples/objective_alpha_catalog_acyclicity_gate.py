"""Emit the Objective Alpha catalog acyclicity gate report."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

from tuc.objective_alpha import (
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID,
)

OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCHEMA_VERSION = (
    "tuc.objective_alpha_catalog_acyclicity_gate_report.v0"
)
OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_CONTRACT = (
    "objective_alpha.catalog_acyclicity_gate.data_only.v0"
)
OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_ID = "objective_alpha_catalog_acyclicity_gate"
OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_STATUS = "PASS"
OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCOPE = (
    "objective_alpha_catalog_entries_below_claim_gates"
)
OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_EVIDENCE_POLICY = (
    "digest_only_source_free_report_scan"
)
OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_FORBIDDEN_DOWNSTREAM_IDS = (
    "objective_alpha_public_evidence_catalog",
    "objective_alpha_public_evidence_catalog_admission_gate",
    "objective_alpha_research_claim",
    "objective_alpha_research_claim_gate",
    "research_scope_claim_gate",
)
OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_REQUIRED_INVARIANTS = (
    "catalog_report_passed",
    "catalog_admission_gate_passed",
    "catalog_entries_do_not_bind_catalog_or_claim_gates",
    "catalog_entry_reports_source_free",
    "forbidden_downstream_ids_absent",
    "dependency_cycle_count_zero",
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_status",
        "catalog_admission_gate_report_digest",
        "catalog_entry_count",
        "catalog_entry_ids",
        "catalog_id",
        "catalog_report_digest",
        "cycle_count",
        "detected_cycles",
        "entry_scan_results",
        "evidence_policy",
        "forbidden_downstream_dependency_ids",
        "forbidden_downstream_dependency_count",
        "gate_contract",
        "gate_id",
        "gate_passed",
        "gate_scope",
        "gate_status",
        "issues",
        "required_invariants",
        "schema_version",
        "source_free",
        "surface_opened",
    }
)
_SCAN_RESULT_KEYS = frozenset(
    {
        "evidence_id",
        "forbidden_downstream_dependency_hits",
        "report_digest",
        "source_free",
    }
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_FORBIDDEN_SOURCE_FRAGMENTS = (
    "@triton.jit",
    '"backend_artifact":',
    '"command_line":',
    '"device_id":',
    '"file_path":',
    '"generated_code":',
    '"host_path":',
    "import os",
    "import triton",
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source":',
    '"raw_source_text":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
    "tl.dot",
    "tl.store",
)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_CATALOG_REPORT_PATH = Path(
    "tests/golden/proofs/objective_alpha_public_evidence_catalog.json"
)
OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_CATALOG_ADMISSION_GATE_REPORT_PATH = Path(
    "tests/golden/proofs/objective_alpha_public_evidence_catalog_admission_gate.json"
)
OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_ENTRY_REPORT_PATHS = {
    "objective_alpha_evidence_extension_policy": Path(
        "tests/golden/proofs/objective_alpha_evidence_extension_policy.json"
    ),
    "runtime_backend_equivalence_portfolio": Path(
        "tests/golden/runtime_backend_equivalence/portfolio_report.json"
    ),
    "source_to_intent_research_kernel_ingress_proof_bundle": Path(
        "tests/golden/frontend/source_to_intent_research_kernel_ingress_proof_bundle.json"
    ),
    "source_intent_mixed_runtime_public_proof_bundle": Path(
        "tests/golden/frontend/source_intent_mixed_runtime_public_proof_bundle.json"
    ),
    "source_to_intent_research_capability_claim_gate": Path(
        "tests/golden/frontend/source_to_intent_research_capability_claim_gate.txt"
    ),
    "first_real_triton_kernel_path": Path(
        "tests/golden/frontend/first_real_triton_kernel_path.json"
    ),
    "real_triton_first_slice_evidence_portfolio": Path(
        "tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json"
    ),
    "oci_source_ingestion_research_proof": Path(
        "tests/golden/frontend/oci_source_ingestion_research_proof_report.json"
    ),
    "oci_source_worker_release_provenance_readiness": Path(
        "tests/golden/frontend/oci_source_worker_release_provenance_readiness_report.json"
    ),
}


class ObjectiveAlphaCatalogAcyclicityGateError(AssertionError):
    """Raised when catalog evidence would depend on downstream claim gates."""


def build_objective_alpha_catalog_acyclicity_gate_report(
    *,
    entry_report_text_overrides: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Return the source-free catalog acyclicity gate report."""

    catalog_text = _read_artifact_text(
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_CATALOG_REPORT_PATH
    )
    catalog_gate_text = _read_artifact_text(
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_CATALOG_ADMISSION_GATE_REPORT_PATH
    )
    catalog_payload = _json_payload(catalog_text, "public_evidence_catalog")
    catalog_gate_payload = _json_payload(
        catalog_gate_text,
        "public_evidence_catalog_admission_gate",
    )
    _assert_catalog_payloads(catalog_payload, catalog_gate_payload)

    entry_texts = _build_entry_report_texts()
    if entry_report_text_overrides:
        for evidence_id, text in entry_report_text_overrides.items():
            if evidence_id not in entry_texts:
                raise ObjectiveAlphaCatalogAcyclicityGateError(
                    "catalog acyclicity override evidence id invalid"
                )
            entry_texts[evidence_id] = text

    scan_results = tuple(
        _scan_entry_report(evidence_id, entry_texts[evidence_id])
        for evidence_id in OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    issues = tuple(
        f"{result['evidence_id']}_binds_downstream_claim_gate"
        for result in scan_results
        if result["forbidden_downstream_dependency_hits"]
    )
    if issues:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity forbidden downstream dependency"
        )

    report: dict[str, object] = {
        "artifact_status": "review_gate",
        "catalog_admission_gate_report_digest": _digest(catalog_gate_text),
        "catalog_entry_count": len(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS),
        "catalog_entry_ids": list(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS),
        "catalog_id": OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID,
        "catalog_report_digest": _digest(catalog_text),
        "cycle_count": 0,
        "detected_cycles": [],
        "entry_scan_results": [dict(result) for result in scan_results],
        "evidence_policy": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_EVIDENCE_POLICY,
        "forbidden_downstream_dependency_ids": list(
            OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_FORBIDDEN_DOWNSTREAM_IDS
        ),
        "forbidden_downstream_dependency_count": len(
            OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_FORBIDDEN_DOWNSTREAM_IDS
        ),
        "gate_contract": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_CONTRACT,
        "gate_id": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_ID,
        "gate_passed": True,
        "gate_scope": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCOPE,
        "gate_status": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_STATUS,
        "issues": [],
        "required_invariants": list(
            OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_REQUIRED_INVARIANTS
        ),
        "schema_version": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCHEMA_VERSION,
        "source_free": True,
        "surface_opened": False,
    }
    assert_objective_alpha_catalog_acyclicity_gate_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the catalog acyclicity gate."""

    return json.dumps(
        build_objective_alpha_catalog_acyclicity_gate_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_objective_alpha_catalog_acyclicity_gate_report_contract(
    report: object,
) -> None:
    """Fail closed unless the report matches the current v0 gate contract."""

    if not isinstance(report, Mapping):
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity report must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity top-level keys drift"
        )
    expected = {
        "artifact_status": "review_gate",
        "catalog_entry_count": len(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS),
        "catalog_id": OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID,
        "cycle_count": 0,
        "evidence_policy": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_EVIDENCE_POLICY,
        "forbidden_downstream_dependency_count": len(
            OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_FORBIDDEN_DOWNSTREAM_IDS
        ),
        "gate_contract": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_CONTRACT,
        "gate_id": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_ID,
        "gate_passed": True,
        "gate_scope": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCOPE,
        "gate_status": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_STATUS,
        "schema_version": OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCHEMA_VERSION,
        "source_free": True,
        "surface_opened": False,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise ObjectiveAlphaCatalogAcyclicityGateError(
                f"catalog acyclicity {key} drift"
            )
    _assert_string_sequence(
        report.get("catalog_entry_ids"),
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS,
        "catalog_entry_ids",
    )
    _assert_string_sequence(
        report.get("forbidden_downstream_dependency_ids"),
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_FORBIDDEN_DOWNSTREAM_IDS,
        "forbidden_downstream_dependency_ids",
    )
    _assert_string_sequence(
        report.get("required_invariants"),
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_REQUIRED_INVARIANTS,
        "required_invariants",
    )
    if report.get("detected_cycles") != []:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity cycles must be empty"
        )
    if report.get("issues") != []:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity issues must be empty"
        )
    _assert_digest(report.get("catalog_report_digest"), "catalog_report_digest")
    _assert_digest(
        report.get("catalog_admission_gate_report_digest"),
        "catalog_admission_gate_report_digest",
    )
    _assert_scan_results(report.get("entry_scan_results"))
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_entry_report_texts() -> dict[str, str]:
    if set(OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_ENTRY_REPORT_PATHS) != set(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    ):
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity entry artifact path map drift"
        )
    return {
        evidence_id: _read_artifact_text(
            OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_ENTRY_REPORT_PATHS[evidence_id]
        )
        for evidence_id in OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    }


def _scan_entry_report(evidence_id: str, text: str) -> Mapping[str, object]:
    if evidence_id not in OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity evidence id invalid"
        )
    _assert_text_is_source_free(text)
    lowered = text.lower()
    hits = tuple(
        downstream_id
        for downstream_id in OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_FORBIDDEN_DOWNSTREAM_IDS
        if downstream_id.lower() in lowered
    )
    return {
        "evidence_id": evidence_id,
        "forbidden_downstream_dependency_hits": list(hits),
        "report_digest": _digest(text),
        "source_free": True,
    }


def _assert_catalog_payloads(
    catalog_payload: Mapping[str, object],
    catalog_gate_payload: Mapping[str, object],
) -> None:
    if catalog_payload.get("catalog_passed") is not True:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity catalog did not pass"
        )
    if catalog_gate_payload.get("gate_passed") is not True:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity catalog gate did not pass"
        )
    if tuple(_string_list(catalog_payload.get("catalog_entries"), "evidence_id")) != (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    ):
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity catalog entry IDs drift"
        )
    if tuple(catalog_gate_payload.get("catalog_evidence_ids", ())) != (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    ):
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity gate entry IDs drift"
        )


def _read_artifact_text(relative_path: Path) -> str:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity artifact path invalid"
        )
    artifact_path = _PROJECT_ROOT / relative_path
    try:
        text = artifact_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity artifact read failed"
        ) from exc
    _assert_text_is_source_free(text)
    return text


def _assert_scan_results(value: object) -> None:
    if not isinstance(value, list):
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity scan results must be list"
        )
    if len(value) != len(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS):
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity scan result count drift"
        )
    for item, expected_id in zip(
        value,
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS,
        strict=True,
    ):
        if not isinstance(item, Mapping) or set(item) != _SCAN_RESULT_KEYS:
            raise ObjectiveAlphaCatalogAcyclicityGateError(
                "catalog acyclicity scan result invalid"
            )
        if item.get("evidence_id") != expected_id:
            raise ObjectiveAlphaCatalogAcyclicityGateError(
                "catalog acyclicity scan evidence id drift"
            )
        if item.get("forbidden_downstream_dependency_hits") != []:
            raise ObjectiveAlphaCatalogAcyclicityGateError(
                "catalog acyclicity forbidden dependency hit"
            )
        if item.get("source_free") is not True:
            raise ObjectiveAlphaCatalogAcyclicityGateError(
                "catalog acyclicity scan source flag drift"
            )
        _assert_digest(item.get("report_digest"), "scan report_digest")


def _json_payload(text: str, label: str) -> Mapping[str, object]:
    _assert_text_is_source_free(text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            f"catalog acyclicity {label} JSON drift"
        ) from exc
    if not isinstance(payload, Mapping):
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            f"catalog acyclicity {label} payload drift"
        )
    return payload


def _string_list(value: object, key: str | None = None) -> list[str]:
    if not isinstance(value, list):
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            "catalog acyclicity expected list"
        )
    result: list[str] = []
    for item in value:
        if key is not None:
            if not isinstance(item, Mapping):
                raise ObjectiveAlphaCatalogAcyclicityGateError(
                    "catalog acyclicity expected mapping list item"
                )
            item = item.get(key)
        if not isinstance(item, str) or not _TOKEN_RE.fullmatch(item):
            raise ObjectiveAlphaCatalogAcyclicityGateError(
                "catalog acyclicity string list item invalid"
            )
        result.append(item)
    return result


def _assert_string_sequence(value: object, expected: tuple[str, ...], label: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            f"catalog acyclicity {label} drift"
        )


def _assert_digest(value: object, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ObjectiveAlphaCatalogAcyclicityGateError(
            f"catalog acyclicity {label} invalid"
        )


def _digest(text: str) -> str:
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_SOURCE_FRAGMENTS:
        if fragment in lowered:
            raise ObjectiveAlphaCatalogAcyclicityGateError(
                f"catalog acyclicity contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
