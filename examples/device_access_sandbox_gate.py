"""Emit the current Device Access Sandbox Gate report."""

from __future__ import annotations

from examples.real_triton_integration_admission_gate import (
    build_current_real_triton_integration_admission_report,
)
from examples.triton_jit_execution_sandbox_gate import (
    build_current_triton_jit_execution_sandbox_report,
)
from tuc.frontend import (
    DEVICE_ACCESS_SANDBOX_REQUIRED_CONTROLS,
    build_device_access_sandbox_report,
    device_access_sandbox_evidence_from_payload,
    dump_device_access_sandbox_report,
    real_triton_integration_admission_report_to_dict,
    triton_jit_execution_sandbox_report_to_dict,
)

DEVICE_ACCESS_SANDBOX_MODEL_EVIDENCE: dict[str, object] = {
    "artifact": "docs.DEVICE_ACCESS_SANDBOX_GATE",
    "device_access_permission": False,
    "device_discovery_permission": False,
    "device_memory_allocation_permission": False,
    "driver_api_call_permission": False,
    "hardware_fingerprint_permission": False,
    "kernel_launch_permission": False,
    "required_controls": list(DEVICE_ACCESS_SANDBOX_REQUIRED_CONTROLS),
    "surface": "device_access",
}


def build_current_device_access_sandbox_report():
    """Build the current data-only device-access sandbox gate report."""

    admission_report = build_current_real_triton_integration_admission_report()
    jit_report = build_current_triton_jit_execution_sandbox_report()
    evidence = (
        device_access_sandbox_evidence_from_payload(
            "real_triton_integration_admission_gate",
            real_triton_integration_admission_report_to_dict(admission_report),
        ),
        device_access_sandbox_evidence_from_payload(
            "triton_jit_execution_sandbox_gate",
            triton_jit_execution_sandbox_report_to_dict(jit_report),
        ),
        device_access_sandbox_evidence_from_payload(
            "device_access_sandbox_model",
            DEVICE_ACCESS_SANDBOX_MODEL_EVIDENCE,
        ),
    )
    return build_device_access_sandbox_report(evidence)


def build_report() -> str:
    """Return stable device-access sandbox evidence."""

    return dump_device_access_sandbox_report(
        build_current_device_access_sandbox_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
