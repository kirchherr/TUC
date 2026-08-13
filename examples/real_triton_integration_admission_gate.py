"""Emit the current Real Triton Integration Admission Gate report."""

from __future__ import annotations

from examples.external_frontend_package_conformance import (
    build_current_external_frontend_package_conformance_report,
)
from examples.triton_integration_readiness import (
    build_current_triton_integration_readiness_report,
)
from tuc.frontend import (
    REAL_TRITON_INTEGRATION_BLOCKED_SURFACES,
    REAL_TRITON_INTEGRATION_REQUIRED_SURFACE_GATES,
    build_real_triton_integration_admission_report,
    dump_real_triton_integration_admission_report,
    external_frontend_package_conformance_report_to_dict,
    real_triton_integration_evidence_from_payload,
    triton_integration_readiness_report_to_dict,
)

REAL_TRITON_INTEGRATION_THREAT_MODEL_EVIDENCE: dict[str, object] = {
    "artifact": "docs.REAL_TRITON_INTEGRATION_THREAT_MODEL",
    "blocked_surfaces": list(REAL_TRITON_INTEGRATION_BLOCKED_SURFACES),
    "device_access_permission": False,
    "external_package_import_permission": False,
    "generated_artifact_execution_permission": False,
    "native_backend_execution_permission": False,
    "plugin_discovery_permission": False,
    "required_surface_gates": list(REAL_TRITON_INTEGRATION_REQUIRED_SURFACE_GATES),
    "source_execution_permission": False,
    "triton_jit_execution_permission": False,
}


def build_current_real_triton_integration_admission_report():
    """Build the current data-only real Triton integration admission gate."""

    external_report = build_current_external_frontend_package_conformance_report()
    readiness_report = build_current_triton_integration_readiness_report()
    evidence = (
        real_triton_integration_evidence_from_payload(
            "external_frontend_package_conformance",
            external_frontend_package_conformance_report_to_dict(external_report),
        ),
        real_triton_integration_evidence_from_payload(
            "real_triton_integration_threat_model",
            REAL_TRITON_INTEGRATION_THREAT_MODEL_EVIDENCE,
        ),
        real_triton_integration_evidence_from_payload(
            "triton_integration_readiness",
            triton_integration_readiness_report_to_dict(readiness_report),
        ),
    )
    return build_real_triton_integration_admission_report(evidence)


def build_report() -> str:
    """Return stable real Triton integration admission evidence."""

    return dump_real_triton_integration_admission_report(
        build_current_real_triton_integration_admission_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
