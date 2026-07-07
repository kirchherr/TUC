"""Emit the current Source Ingestion Quarantine Gate report."""

from __future__ import annotations

from examples.real_triton_integration_admission_gate import (
    build_current_real_triton_integration_admission_report,
)
from tuc.frontend import (
    SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
    TRITON_SOURCE_PREFLIGHT_CONTRACT,
    build_source_ingestion_quarantine_report,
    dump_source_ingestion_quarantine_report,
    real_triton_integration_admission_report_to_dict,
    source_ingestion_quarantine_evidence_from_payload,
)

TRITON_SOURCE_THREAT_MODEL_EVIDENCE: dict[str, object] = {
    "artifact": "docs.TRITON_SOURCE_THREAT_MODEL",
    "diagnostic_leakage_blocked": True,
    "source_buffers_are_untrusted": True,
    "source_execution_permission": False,
    "surface": "direct_source_ingestion",
}

TRITON_SOURCE_PREFLIGHT_EVIDENCE: dict[str, object] = {
    "artifact": "docs.TRITON_SOURCE_PREFLIGHT",
    "contract": TRITON_SOURCE_PREFLIGHT_CONTRACT,
    "execution_permission": False,
    "produces_compute_graph": False,
    "produces_hac_ir": False,
    "produces_runtime_plan": False,
}

SOURCE_TO_INTENT_PARSER_GATE_EVIDENCE: dict[str, object] = {
    "artifact": "docs.SOURCE_TO_INTENT_PARSER_GATE",
    "default_parser_enabled": False,
    "gate_contract": SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
    "source_to_compute_graph": False,
    "source_to_hac_ir": False,
}


def build_current_source_ingestion_quarantine_report():
    """Build the current data-only source-ingestion quarantine gate report."""

    admission_report = build_current_real_triton_integration_admission_report()
    evidence = (
        source_ingestion_quarantine_evidence_from_payload(
            "real_triton_integration_admission_gate",
            real_triton_integration_admission_report_to_dict(admission_report),
        ),
        source_ingestion_quarantine_evidence_from_payload(
            "source_to_intent_parser_gate",
            SOURCE_TO_INTENT_PARSER_GATE_EVIDENCE,
        ),
        source_ingestion_quarantine_evidence_from_payload(
            "triton_source_preflight",
            TRITON_SOURCE_PREFLIGHT_EVIDENCE,
        ),
        source_ingestion_quarantine_evidence_from_payload(
            "triton_source_threat_model",
            TRITON_SOURCE_THREAT_MODEL_EVIDENCE,
        ),
    )
    return build_source_ingestion_quarantine_report(evidence)


def build_report() -> str:
    """Return stable source-ingestion quarantine evidence."""

    return dump_source_ingestion_quarantine_report(
        build_current_source_ingestion_quarantine_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
