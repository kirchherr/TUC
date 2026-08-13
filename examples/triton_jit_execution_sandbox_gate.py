"""Emit the current Triton JIT Execution Sandbox Gate report."""

from __future__ import annotations

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
from tuc.frontend import (
    TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_CONTROLS,
    build_triton_jit_execution_sandbox_report,
    dump_triton_jit_execution_sandbox_report,
    package_import_sandbox_report_to_dict,
    plugin_discovery_allowlist_report_to_dict,
    real_triton_integration_admission_report_to_dict,
    source_ingestion_quarantine_report_to_dict,
    triton_jit_execution_sandbox_evidence_from_payload,
)

TRITON_JIT_EXECUTION_SANDBOX_MODEL_EVIDENCE: dict[str, object] = {
    "artifact": "docs.TRITON_JIT_EXECUTION_SANDBOX_GATE",
    "backend_binary_emission_permission": False,
    "cache_write_permission": False,
    "device_access_permission": False,
    "generated_artifact_execution_permission": False,
    "kernel_launch_permission": False,
    "required_controls": list(TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_CONTROLS),
    "surface": "triton_jit_execution",
    "triton_jit_execution_permission": False,
}


def build_current_triton_jit_execution_sandbox_report():
    """Build the current data-only Triton-JIT execution sandbox report."""

    package_report = build_current_package_import_sandbox_report()
    plugin_report = build_current_plugin_discovery_allowlist_report()
    admission_report = build_current_real_triton_integration_admission_report()
    quarantine_report = build_current_source_ingestion_quarantine_report()
    evidence = (
        triton_jit_execution_sandbox_evidence_from_payload(
            "package_import_sandbox_gate",
            package_import_sandbox_report_to_dict(package_report),
        ),
        triton_jit_execution_sandbox_evidence_from_payload(
            "plugin_discovery_allowlist_gate",
            plugin_discovery_allowlist_report_to_dict(plugin_report),
        ),
        triton_jit_execution_sandbox_evidence_from_payload(
            "real_triton_integration_admission_gate",
            real_triton_integration_admission_report_to_dict(admission_report),
        ),
        triton_jit_execution_sandbox_evidence_from_payload(
            "source_ingestion_quarantine_gate",
            source_ingestion_quarantine_report_to_dict(quarantine_report),
        ),
        triton_jit_execution_sandbox_evidence_from_payload(
            "triton_jit_execution_sandbox_model",
            TRITON_JIT_EXECUTION_SANDBOX_MODEL_EVIDENCE,
        ),
    )
    return build_triton_jit_execution_sandbox_report(evidence)


def build_report() -> str:
    """Return stable Triton-JIT execution sandbox evidence."""

    return dump_triton_jit_execution_sandbox_report(
        build_current_triton_jit_execution_sandbox_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
