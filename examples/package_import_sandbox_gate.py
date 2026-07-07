"""Emit the current Package Import Sandbox Gate report."""

from __future__ import annotations

from examples.external_frontend_package_conformance import (
    build_current_external_frontend_package_conformance_report,
)
from examples.real_triton_integration_admission_gate import (
    build_current_real_triton_integration_admission_report,
)
from examples.source_ingestion_quarantine_gate import (
    build_current_source_ingestion_quarantine_report,
)
from tuc.frontend import (
    PACKAGE_IMPORT_SANDBOX_REQUIRED_CONTROLS,
    build_package_import_sandbox_report,
    dump_package_import_sandbox_report,
    external_frontend_package_conformance_report_to_dict,
    package_import_sandbox_evidence_from_payload,
    real_triton_integration_admission_report_to_dict,
    source_ingestion_quarantine_report_to_dict,
)

PACKAGE_IMPORT_SANDBOX_MODEL_EVIDENCE: dict[str, object] = {
    "artifact": "docs.PACKAGE_IMPORT_SANDBOX_GATE",
    "entrypoint_discovery_permission": False,
    "external_package_import_permission": False,
    "network_access_permission": False,
    "package_code_execution_permission": False,
    "python_import_permission": False,
    "required_controls": list(PACKAGE_IMPORT_SANDBOX_REQUIRED_CONTROLS),
    "surface": "frontend_package_import",
}


def build_current_package_import_sandbox_report():
    """Build the current data-only package-import sandbox gate report."""

    external_report = build_current_external_frontend_package_conformance_report()
    admission_report = build_current_real_triton_integration_admission_report()
    quarantine_report = build_current_source_ingestion_quarantine_report()
    evidence = (
        package_import_sandbox_evidence_from_payload(
            "external_frontend_package_conformance",
            external_frontend_package_conformance_report_to_dict(external_report),
        ),
        package_import_sandbox_evidence_from_payload(
            "package_import_sandbox_model",
            PACKAGE_IMPORT_SANDBOX_MODEL_EVIDENCE,
        ),
        package_import_sandbox_evidence_from_payload(
            "real_triton_integration_admission_gate",
            real_triton_integration_admission_report_to_dict(admission_report),
        ),
        package_import_sandbox_evidence_from_payload(
            "source_ingestion_quarantine_gate",
            source_ingestion_quarantine_report_to_dict(quarantine_report),
        ),
    )
    return build_package_import_sandbox_report(evidence)


def build_report() -> str:
    """Return stable package-import sandbox evidence."""

    return dump_package_import_sandbox_report(
        build_current_package_import_sandbox_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
