"""Run the CI-facing Source Intent Frontend Conformance Gate."""

try:
    from examples.source_intent_frontend_conformance import (
        build_source_intent_frontend_conformance_cases,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_intent_frontend_conformance import (  # type: ignore[no-redef]
        build_source_intent_frontend_conformance_cases,
    )

from tuc.frontend import (
    SourceIntentFrontendConformanceReport,
    run_source_intent_frontend_conformance,
)

SOURCE_INTENT_FRONTEND_CONFORMANCE_GATE_CONTRACT = (
    "source_intent_frontend_conformance_gate.ci.v0"
)
DEFAULT_FRONTEND_NAME = "example-source-intent-frontend"
REQUIRED_RETURN_CONFORMANCE_CASES = (
    "valid_source_intent_return_mlp",
    "reject_return_unknown_tensor",
    "reject_return_intermediate_tensor",
    "reject_duplicate_public_returns",
)
BLOCKED_FRONTEND_EXECUTION_SURFACES = (
    "device_access",
    "file_system_access",
    "frontend_package_import",
    "generated_artifact_execution",
    "jit_execution",
    "network_access",
    "plugin_discovery",
    "source_parsing",
    "subprocess_execution",
)


class SourceIntentFrontendConformanceGateError(AssertionError):
    """Raised when Source Intent frontend conformance gate evidence is incomplete."""


def build_gate_report(
    *,
    conformance_report: SourceIntentFrontendConformanceReport | None = None,
) -> str:
    """Return the stable CI-facing Source Intent frontend gate report."""

    report = (
        run_source_intent_frontend_conformance(
            DEFAULT_FRONTEND_NAME,
            build_source_intent_frontend_conformance_cases(),
        )
        if conformance_report is None
        else conformance_report
    )
    _assert_conformance_passed(report)
    _assert_return_conformance_covered(report)
    return _render_gate_report(report)


def main() -> None:
    print(build_gate_report(), end="")


def _assert_conformance_passed(
    report: SourceIntentFrontendConformanceReport,
) -> None:
    if not isinstance(report, SourceIntentFrontendConformanceReport):
        raise SourceIntentFrontendConformanceGateError(
            "source intent frontend conformance failed: not a report object"
        )
    if not report.passed:
        issues = ",".join(
            f"{issue.case_name}:{issue.message}" for issue in report.issues
        )
        raise SourceIntentFrontendConformanceGateError(
            f"source intent frontend conformance failed: {issues}"
        )
    if report.accepted_case_count < 1:
        raise SourceIntentFrontendConformanceGateError(
            "source intent frontend conformance failed: no accepted cases"
        )
    if report.rejected_case_count < 1:
        raise SourceIntentFrontendConformanceGateError(
            "source intent frontend conformance failed: no rejected cases"
        )


def _assert_return_conformance_covered(
    report: SourceIntentFrontendConformanceReport,
) -> None:
    checked_cases = frozenset(report.checked_cases)
    missing_cases = tuple(
        case_name
        for case_name in REQUIRED_RETURN_CONFORMANCE_CASES
        if case_name not in checked_cases
    )
    if missing_cases:
        missing = ",".join(missing_cases)
        raise SourceIntentFrontendConformanceGateError(
            "source intent frontend return conformance coverage failed: "
            f"missing {missing}"
        )


def _render_gate_report(report: SourceIntentFrontendConformanceReport) -> str:
    lines = [
        "source_intent.frontend_conformance_gate "
        "@source_intent_frontend_conformance_gate_v0 {"
    ]
    lines.append(
        f'  gate_contract = "{SOURCE_INTENT_FRONTEND_CONFORMANCE_GATE_CONTRACT}"'
    )
    lines.append('  frontend_conformance = "passed"')
    lines.append(f'  frontend_name = "{report.frontend_name}"')
    lines.append(f'  accepted_cases = "{report.accepted_case_count}"')
    lines.append(f'  rejected_cases = "{report.rejected_case_count}"')
    lines.append(f'  checked_cases = "{len(report.checked_cases)}"')
    lines.append('  return_conformance = "covered"')
    lines.append(
        "  required_return_conformance_cases = "
        f'"{",".join(REQUIRED_RETURN_CONFORMANCE_CASES)}"'
    )
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(BLOCKED_FRONTEND_EXECUTION_SURFACES)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
