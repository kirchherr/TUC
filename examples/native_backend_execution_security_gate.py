"""Emit the current Native Backend Execution Security Gate report."""

from __future__ import annotations

from examples.backend_plugin_lifecycle_policy import (
    build_current_backend_plugin_lifecycle_policy_report,
)
from examples.device_access_sandbox_gate import (
    build_current_device_access_sandbox_report,
)
from examples.generated_artifact_quarantine_gate import (
    build_current_generated_artifact_quarantine_report,
)
from examples.real_triton_integration_admission_gate import (
    build_current_real_triton_integration_admission_report,
)
from tuc import backend_plugin_lifecycle_policy_report_to_dict
from tuc.frontend import (
    NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_CONTROLS,
    build_native_backend_execution_security_report,
    device_access_sandbox_report_to_dict,
    dump_native_backend_execution_security_report,
    generated_artifact_quarantine_report_to_dict,
    native_backend_execution_security_evidence_from_payload,
    real_triton_integration_admission_report_to_dict,
)

NATIVE_BACKEND_EXECUTION_SECURITY_MODEL_EVIDENCE: dict[str, object] = {
    "abi_loading_permission": False,
    "artifact": "docs.NATIVE_BACKEND_EXECUTION_SECURITY_GATE",
    "backend_plugin_execution_permission": False,
    "capability_claims_from_native_code_permission": False,
    "dynamic_library_loading_permission": False,
    "ffi_call_permission": False,
    "native_backend_execution_permission": False,
    "required_controls": list(NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_CONTROLS),
    "surface": "native_backend_execution",
    "symbol_resolution_permission": False,
}


def build_current_native_backend_execution_security_report():
    """Build the current data-only native-backend execution security report."""

    admission_report = build_current_real_triton_integration_admission_report()
    artifact_report = build_current_generated_artifact_quarantine_report()
    device_report = build_current_device_access_sandbox_report()
    lifecycle_report = build_current_backend_plugin_lifecycle_policy_report()
    evidence = (
        native_backend_execution_security_evidence_from_payload(
            "real_triton_integration_admission_gate",
            real_triton_integration_admission_report_to_dict(admission_report),
        ),
        native_backend_execution_security_evidence_from_payload(
            "generated_artifact_quarantine_gate",
            generated_artifact_quarantine_report_to_dict(artifact_report),
        ),
        native_backend_execution_security_evidence_from_payload(
            "device_access_sandbox_gate",
            device_access_sandbox_report_to_dict(device_report),
        ),
        native_backend_execution_security_evidence_from_payload(
            "backend_plugin_lifecycle_policy",
            backend_plugin_lifecycle_policy_report_to_dict(lifecycle_report),
        ),
        native_backend_execution_security_evidence_from_payload(
            "native_backend_execution_security_model",
            NATIVE_BACKEND_EXECUTION_SECURITY_MODEL_EVIDENCE,
        ),
    )
    return build_native_backend_execution_security_report(evidence)


def build_report() -> str:
    """Return stable native-backend execution security evidence."""

    return dump_native_backend_execution_security_report(
        build_current_native_backend_execution_security_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
