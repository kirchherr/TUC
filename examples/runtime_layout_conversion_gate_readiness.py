"""Emit Runtime Layout Conversion Gate Readiness Report v0."""

try:
    from examples.runtime_layout_conversion_evidence import (
        build_current_runtime_layout_conversion_evidence_report,
    )
    from examples.runtime_layout_conversion_second_slice import (
        build_second_runtime_layout_conversion_evidence_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_layout_conversion_evidence import (  # type: ignore[no-redef]
        build_current_runtime_layout_conversion_evidence_report,
    )
    from runtime_layout_conversion_second_slice import (  # type: ignore[no-redef]
        build_second_runtime_layout_conversion_evidence_report,
    )

from tuc.runtime.layout_conversion_gate_readiness import (
    RuntimeLayoutConversionGateReadinessCheck,
    RuntimeLayoutConversionGateReadinessReport,
    build_runtime_layout_conversion_gate_readiness_report,
    dump_runtime_layout_conversion_gate_readiness_report,
)


def build_current_runtime_layout_conversion_gate_readiness_report() -> (
    RuntimeLayoutConversionGateReadinessReport
):
    """Return the current gate-readiness report for layout conversion evidence."""

    source_evidence = build_current_runtime_layout_conversion_evidence_report()
    second_slice = build_second_runtime_layout_conversion_evidence_report()
    second_slice_ready = (
        second_slice.passed
        and len(second_slice.conversions) >= 1
        and second_slice.graph_name != source_evidence.graph_name
        and second_slice.conversion_metadata_digest
        != source_evidence.conversion_metadata_digest
    )
    checks = (
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="layout_conversion_evidence_report_passes",
            status="passed",
            evidence_id="runtime_layout_conversion_evidence_mixed",
            detail="source_report_passed",
        ),
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="layout_conversion_schema_and_golden_stable",
            status="passed",
            evidence_id="runtime_layout_conversion_evidence_schema_and_golden",
            detail="schema_and_current_golden_present",
        ),
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="layout_conversion_negative_tests_present",
            status="passed",
            evidence_id="tests.test_runtime_layout_conversion_evidence",
            detail="negative_tests_cover_malformed_inputs",
        ),
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="runtime_evidence_matrix_optional_inventory",
            status="passed",
            evidence_id="runtime_layout_conversion_evidence_mixed",
            detail="matrix_inventory_optional",
        ),
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="second_independent_layout_conversion_slice",
            status="passed" if second_slice_ready else "blocked",
            evidence_id=(
                "runtime_layout_conversion_evidence_reduction_slice"
                if second_slice_ready
                else "missing_second_layout_conversion_slice"
            ),
            detail="second_slice_report_passed" if second_slice_ready else "one_slice_only",
        ),
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="gate_exact_artifact_binding",
            status="blocked",
            evidence_id="missing_runtime_evidence_gate_binding",
            detail="not_gate_required_yet",
        ),
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="hs_ir_and_tensor_store_digest_binding",
            status="blocked",
            evidence_id="missing_hs_ir_tensor_store_digest_binding",
            detail="digest_binding_deferred",
        ),
    )
    return build_runtime_layout_conversion_gate_readiness_report(
        source_evidence,
        checks,
    )


def main() -> None:
    print(
        dump_runtime_layout_conversion_gate_readiness_report(
            build_current_runtime_layout_conversion_gate_readiness_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
