"""Emit the current Real Triton Surface Gate Completion report."""

from __future__ import annotations

from examples.device_access_sandbox_gate import build_current_device_access_sandbox_report
from examples.generated_artifact_quarantine_gate import (
    build_current_generated_artifact_quarantine_report,
)
from examples.native_backend_execution_security_gate import (
    build_current_native_backend_execution_security_report,
)
from examples.package_import_sandbox_gate import (
    build_current_package_import_sandbox_report,
)
from examples.plugin_discovery_allowlist_gate import (
    build_current_plugin_discovery_allowlist_report,
)
from examples.real_triton_integration_admission_gate import (
    build_current_real_triton_integration_admission_report,
)
from examples.source_ingestion_quarantine_gate import (
    build_current_source_ingestion_quarantine_report,
)
from examples.triton_jit_execution_sandbox_gate import (
    build_current_triton_jit_execution_sandbox_report,
)
from tuc.frontend import (
    build_real_triton_surface_gate_completion_report,
    device_access_sandbox_report_to_dict,
    dump_real_triton_surface_gate_completion_report,
    generated_artifact_quarantine_report_to_dict,
    native_backend_execution_security_report_to_dict,
    package_import_sandbox_report_to_dict,
    plugin_discovery_allowlist_report_to_dict,
    real_triton_integration_admission_report_to_dict,
    real_triton_surface_gate_completion_digest_payload,
    real_triton_surface_gate_evidence_from_payload,
    source_ingestion_quarantine_report_to_dict,
    triton_jit_execution_sandbox_report_to_dict,
)


def build_current_real_triton_surface_gate_completion_report():
    """Build the current data-only Real Triton surface-gate completion report."""

    admission_report = build_current_real_triton_integration_admission_report()
    source_report = build_current_source_ingestion_quarantine_report()
    package_report = build_current_package_import_sandbox_report()
    plugin_report = build_current_plugin_discovery_allowlist_report()
    jit_report = build_current_triton_jit_execution_sandbox_report()
    device_report = build_current_device_access_sandbox_report()
    artifact_report = build_current_generated_artifact_quarantine_report()
    native_report = build_current_native_backend_execution_security_report()

    admission_payload = real_triton_integration_admission_report_to_dict(
        admission_report
    )
    surface_gate_evidence = (
        real_triton_surface_gate_evidence_from_payload(
            "source_ingestion_quarantine_gate",
            source_ingestion_quarantine_report_to_dict(source_report),
        ),
        real_triton_surface_gate_evidence_from_payload(
            "package_import_sandbox_gate",
            package_import_sandbox_report_to_dict(package_report),
        ),
        real_triton_surface_gate_evidence_from_payload(
            "plugin_discovery_allowlist_gate",
            plugin_discovery_allowlist_report_to_dict(plugin_report),
        ),
        real_triton_surface_gate_evidence_from_payload(
            "triton_jit_execution_sandbox_gate",
            triton_jit_execution_sandbox_report_to_dict(jit_report),
        ),
        real_triton_surface_gate_evidence_from_payload(
            "device_access_sandbox_gate",
            device_access_sandbox_report_to_dict(device_report),
        ),
        real_triton_surface_gate_evidence_from_payload(
            "generated_artifact_quarantine_gate",
            generated_artifact_quarantine_report_to_dict(artifact_report),
        ),
        real_triton_surface_gate_evidence_from_payload(
            "native_backend_execution_security_gate",
            native_backend_execution_security_report_to_dict(native_report),
        ),
    )
    return build_real_triton_surface_gate_completion_report(
        real_triton_surface_gate_completion_digest_payload(admission_payload),
        surface_gate_evidence,
    )


def build_report() -> str:
    """Return stable Real Triton surface-gate completion evidence."""

    return dump_real_triton_surface_gate_completion_report(
        build_current_real_triton_surface_gate_completion_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()