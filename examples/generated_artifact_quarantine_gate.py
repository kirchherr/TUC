"""Emit the current Generated Artifact Quarantine Gate report."""

from __future__ import annotations

from examples.device_access_sandbox_gate import (
    build_current_device_access_sandbox_report,
)
from examples.real_triton_integration_admission_gate import (
    build_current_real_triton_integration_admission_report,
)
from examples.triton_jit_execution_sandbox_gate import (
    build_current_triton_jit_execution_sandbox_report,
)
from tuc.frontend import (
    GENERATED_ARTIFACT_QUARANTINE_REQUIRED_CONTROLS,
    build_generated_artifact_quarantine_report,
    device_access_sandbox_report_to_dict,
    dump_generated_artifact_quarantine_report,
    generated_artifact_quarantine_evidence_from_payload,
    real_triton_integration_admission_report_to_dict,
    triton_jit_execution_sandbox_report_to_dict,
)

GENERATED_ARTIFACT_QUARANTINE_MODEL_EVIDENCE: dict[str, object] = {
    "artifact": "docs.GENERATED_ARTIFACT_QUARANTINE_GATE",
    "artifact_cache_access_permission": False,
    "artifact_emission_permission": False,
    "artifact_execution_permission": False,
    "artifact_write_permission": False,
    "backend_binary_emission_permission": False,
    "executable_permission": False,
    "required_controls": list(GENERATED_ARTIFACT_QUARANTINE_REQUIRED_CONTROLS),
    "surface": "generated_artifact_execution",
}


def build_current_generated_artifact_quarantine_report():
    """Build the current data-only generated-artifact quarantine gate report."""

    admission_report = build_current_real_triton_integration_admission_report()
    jit_report = build_current_triton_jit_execution_sandbox_report()
    device_report = build_current_device_access_sandbox_report()
    evidence = (
        generated_artifact_quarantine_evidence_from_payload(
            "real_triton_integration_admission_gate",
            real_triton_integration_admission_report_to_dict(admission_report),
        ),
        generated_artifact_quarantine_evidence_from_payload(
            "triton_jit_execution_sandbox_gate",
            triton_jit_execution_sandbox_report_to_dict(jit_report),
        ),
        generated_artifact_quarantine_evidence_from_payload(
            "device_access_sandbox_gate",
            device_access_sandbox_report_to_dict(device_report),
        ),
        generated_artifact_quarantine_evidence_from_payload(
            "generated_artifact_quarantine_model",
            GENERATED_ARTIFACT_QUARANTINE_MODEL_EVIDENCE,
        ),
    )
    return build_generated_artifact_quarantine_report(evidence)


def build_report() -> str:
    """Return stable generated-artifact quarantine evidence."""

    return dump_generated_artifact_quarantine_report(
        build_current_generated_artifact_quarantine_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
