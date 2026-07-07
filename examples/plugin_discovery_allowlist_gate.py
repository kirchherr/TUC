"""Emit the current Plugin Discovery Allowlist Gate report."""

from __future__ import annotations

from examples.external_frontend_package_conformance import (
    build_current_external_frontend_package_conformance_report,
)
from examples.package_import_sandbox_gate import (
    build_current_package_import_sandbox_report,
)
from examples.real_triton_integration_admission_gate import (
    build_current_real_triton_integration_admission_report,
)
from tuc.frontend import (
    PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_CONTROLS,
    build_plugin_discovery_allowlist_report,
    dump_plugin_discovery_allowlist_report,
    external_frontend_package_conformance_report_to_dict,
    package_import_sandbox_report_to_dict,
    plugin_discovery_allowlist_evidence_from_payload,
    real_triton_integration_admission_report_to_dict,
)

PLUGIN_DISCOVERY_ALLOWLIST_MODEL_EVIDENCE: dict[str, object] = {
    "allowlist_entry_kind": "manifest_id",
    "artifact": "docs.PLUGIN_DISCOVERY_ALLOWLIST_GATE",
    "capability_claims_from_code_permission": False,
    "entrypoint_discovery_permission": False,
    "plugin_code_execution_permission": False,
    "plugin_discovery_permission": False,
    "registry_scan_permission": False,
    "required_controls": list(PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_CONTROLS),
    "surface": "plugin_discovery",
}


def build_current_plugin_discovery_allowlist_report():
    """Build the current data-only plugin-discovery allowlist gate report."""

    external_report = build_current_external_frontend_package_conformance_report()
    package_report = build_current_package_import_sandbox_report()
    admission_report = build_current_real_triton_integration_admission_report()
    evidence = (
        plugin_discovery_allowlist_evidence_from_payload(
            "external_frontend_package_conformance",
            external_frontend_package_conformance_report_to_dict(external_report),
        ),
        plugin_discovery_allowlist_evidence_from_payload(
            "package_import_sandbox_gate",
            package_import_sandbox_report_to_dict(package_report),
        ),
        plugin_discovery_allowlist_evidence_from_payload(
            "plugin_discovery_allowlist_model",
            PLUGIN_DISCOVERY_ALLOWLIST_MODEL_EVIDENCE,
        ),
        plugin_discovery_allowlist_evidence_from_payload(
            "real_triton_integration_admission_gate",
            real_triton_integration_admission_report_to_dict(admission_report),
        ),
    )
    return build_plugin_discovery_allowlist_report(evidence)


def build_report() -> str:
    """Return stable plugin-discovery allowlist evidence."""

    return dump_plugin_discovery_allowlist_report(
        build_current_plugin_discovery_allowlist_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
