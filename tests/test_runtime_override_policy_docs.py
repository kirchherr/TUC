from __future__ import annotations

from pathlib import Path


def test_runtime_override_policy_documents_allowed_boundary() -> None:
    text = Path("docs/RUNTIME_OVERRIDE_POLICY.md").read_text(encoding="utf-8")

    for required in (
        "schema_version",
        "Operation-scoped",
        "declarative data",
        "BackendRegistry",
        "require_backend",
        "prefer_backend",
        "deny_backend",
        "compiler decision reports",
        "runtime-plan dumps",
        "RuntimeOverrideSet.from_manifest",
        "tuc.runtime_overrides.v0",
    ):
        assert required in text


def test_runtime_override_policy_documents_hard_limits() -> None:
    text = Path("docs/RUNTIME_OVERRIDE_POLICY.md").read_text(encoding="utf-8")

    for forbidden_surface in (
        "Change mathematical semantics",
        "Bypass `BackendRegistry.diagnose_operation_support`",
        "accepted backend candidate",
        "Change HAC-IR attributes",
        "Execute backend code",
        "Discover plugins",
        "Import modules",
        "Spawn subprocesses",
        "Load dynamic libraries",
        "Access devices",
        "Execute generated artifacts",
        "Touch the network",
        "Read host paths",
        "environment variables",
    ):
        assert forbidden_surface in text


def test_runtime_override_policy_documents_fail_closed_gate() -> None:
    text = Path("docs/RUNTIME_OVERRIDE_POLICY.md").read_text(encoding="utf-8")

    for required in (
        "Fail-Closed Rejection Cases",
        "Unknown or unsupported `schema_version`",
        "Unknown fields",
        "Unknown operation names",
        "Unknown backend names",
        "Contradictory `require_backend` and `deny_backend` actions",
        "Simultaneous `require_backend` and `prefer_backend` actions",
        "Deny rules that remove every valid candidate",
        "Negative tests for every fail-closed case",
        "Golden compiler decision-report fixtures",
        "Golden runtime-plan fixtures",
    ):
        assert required in text


def test_runtime_override_policy_documents_current_evidence() -> None:
    text = Path("docs/RUNTIME_OVERRIDE_POLICY.md").read_text(encoding="utf-8")
    rfc = Path("rfcs/0043-runtime-manual-overrides-v0.md").read_text(encoding="utf-8")

    for required in (
        "RuntimeOverrideSet",
        "RuntimeOverrideRule",
        "RuntimeOverrideEffect",
        "RuntimeOverrideAction",
        "RuntimeOverrideError",
        "tests/golden/runtime_plans/manual_override_require.txt",
        "tests/golden/compiler_decisions/manual_override_require.txt",
    ):
        assert required in text or required in rfc


def test_runtime_override_policy_is_linked_from_core_docs() -> None:
    for path in (
        "README.md",
        "docs/COMPILER_DECISION_REPORT.md",
        "docs/RUNTIME_PLAN.md",
        "docs/SECURITY_BASELINE.md",
        "docs/REVIEW_POLICY.md",
        "ROADMAP.md",
        "rfcs/0042-runtime-manual-override-policy.md",
        "rfcs/0043-runtime-manual-overrides-v0.md",
    ):
        text = Path(path).read_text(encoding="utf-8")
        assert "RUNTIME_OVERRIDE_POLICY.md" in text
