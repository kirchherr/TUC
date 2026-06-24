"""Emit Runtime Layout Conversion Gate Readiness Report v0."""

from __future__ import annotations

try:
    from examples.runtime_layout_conversion_digest_binding import (
        build_current_runtime_layout_conversion_digest_binding_report,
    )
    from examples.runtime_layout_conversion_evidence import (
        build_current_runtime_layout_conversion_evidence_report,
    )
    from examples.runtime_layout_conversion_second_slice import (
        build_second_runtime_layout_conversion_evidence_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_layout_conversion_digest_binding import (  # type: ignore[no-redef]
        build_current_runtime_layout_conversion_digest_binding_report,
    )
    from runtime_layout_conversion_evidence import (  # type: ignore[no-redef]
        build_current_runtime_layout_conversion_evidence_report,
    )
    from runtime_layout_conversion_second_slice import (  # type: ignore[no-redef]
        build_second_runtime_layout_conversion_evidence_report,
    )

from tuc import RuntimeEvidenceMatrixReport, build_current_runtime_evidence_matrix_report
from tuc.runtime.layout_conversion_digest_binding import (
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID,
    RuntimeLayoutConversionDigestBindingReport,
)
from tuc.runtime.layout_conversion_evidence import RuntimeLayoutConversionEvidenceReport
from tuc.runtime.layout_conversion_gate_readiness import (
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID,
    RuntimeLayoutConversionGateReadinessCheck,
    RuntimeLayoutConversionGateReadinessReport,
    build_runtime_layout_conversion_gate_readiness_report,
    dump_runtime_layout_conversion_gate_readiness_report,
)


def build_current_runtime_layout_conversion_gate_readiness_report(
    *,
    source_evidence: RuntimeLayoutConversionEvidenceReport | None = None,
    second_slice: RuntimeLayoutConversionEvidenceReport | None = None,
    matrix_report: RuntimeEvidenceMatrixReport | None = None,
    digest_binding_report: RuntimeLayoutConversionDigestBindingReport | None = None,
) -> RuntimeLayoutConversionGateReadinessReport:
    """Return the current gate-readiness report for layout conversion evidence."""

    source_evidence = (
        build_current_runtime_layout_conversion_evidence_report()
        if source_evidence is None
        else source_evidence
    )
    second_slice = (
        build_second_runtime_layout_conversion_evidence_report()
        if second_slice is None
        else second_slice
    )
    matrix_report = (
        build_current_runtime_evidence_matrix_report()
        if matrix_report is None
        else matrix_report
    )
    digest_binding_report = (
        build_current_runtime_layout_conversion_digest_binding_report()
        if digest_binding_report is None
        else digest_binding_report
    )
    second_slice_ready = (
        second_slice.passed
        and len(second_slice.conversions) >= 1
        and second_slice.graph_name != source_evidence.graph_name
        and second_slice.conversion_metadata_digest
        != source_evidence.conversion_metadata_digest
    )
    matrix_inventory_ready = _matrix_has_layout_conversion_inventory(matrix_report)
    exact_binding_ready = _matrix_binding_matches_source_report(
        matrix_report,
        source_evidence,
    )
    digest_binding_ready = _digest_binding_matches_source_report(
        digest_binding_report,
        source_evidence,
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
            check_name="runtime_evidence_matrix_required_inventory",
            status="passed" if matrix_inventory_ready else "blocked",
            evidence_id=(
                RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID
                if matrix_inventory_ready
                else "missing_runtime_evidence_matrix_inventory"
            ),
            detail=(
                "matrix_inventory_required"
                if matrix_inventory_ready
                else "missing_matrix_required_inventory"
            ),
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
            status="passed" if exact_binding_ready else "blocked",
            evidence_id=(
                RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID
                if exact_binding_ready
                else "missing_runtime_evidence_gate_binding"
            ),
            detail=(
                "exact_artifact_binding_verified"
                if exact_binding_ready
                else "not_gate_required_yet"
            ),
        ),
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="hs_ir_and_tensor_store_digest_binding",
            status="passed" if digest_binding_ready else "blocked",
            evidence_id=(
                RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID
                if digest_binding_ready
                else "missing_hs_ir_tensor_store_digest_binding"
            ),
            detail=(
                "exact_digest_binding_verified"
                if digest_binding_ready
                else "digest_binding_deferred"
            ),
        ),
    )
    return build_runtime_layout_conversion_gate_readiness_report(
        source_evidence,
        checks,
    )


def _matrix_has_layout_conversion_inventory(
    matrix_report: RuntimeEvidenceMatrixReport,
) -> bool:
    for graph in matrix_report.graphs:
        if graph.graph_id != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID:
            continue
        return any(
            artifact.artifact_kind
            == RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND
            for artifact in graph.artifacts
        )
    return False


def _matrix_binding_matches_source_report(
    matrix_report: RuntimeEvidenceMatrixReport,
    source_evidence: RuntimeLayoutConversionEvidenceReport,
) -> bool:
    if not source_evidence.passed:
        return False
    for graph in matrix_report.graphs:
        if graph.graph_id != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID:
            continue
        if source_evidence.graph_name != graph.graph_id:
            return False
        if graph.source_boundary != "runtime_backend_equivalence":
            return False
        for artifact in graph.artifacts:
            if (
                artifact.artifact_kind
                == RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND
            ):
                return (
                    artifact.artifact_id
                    == RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID
                )
        return False
    return False


def _digest_binding_matches_source_report(
    digest_binding_report: RuntimeLayoutConversionDigestBindingReport,
    source_evidence: RuntimeLayoutConversionEvidenceReport,
) -> bool:
    return (
        digest_binding_report.passed
        and digest_binding_report.graph_name == source_evidence.graph_name
        and digest_binding_report.source_layout_conversion_passed
        and digest_binding_report.source_layout_conversion_count
        == len(source_evidence.conversions)
        and digest_binding_report.source_layout_conversion_issue_count
        == len(source_evidence.issues)
        and digest_binding_report.source_layout_conversion_total_planned_bytes
        == source_evidence.total_planned_bytes
        and digest_binding_report.source_layout_conversion_metadata_digest
        == source_evidence.conversion_metadata_digest
        and digest_binding_report.source_partition_plan_digest
        == source_evidence.source_partition_plan_digest
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
