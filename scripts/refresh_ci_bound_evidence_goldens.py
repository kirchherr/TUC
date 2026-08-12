"""Check or refresh the evidence goldens bound to CI and release workflows."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path, PurePosixPath
from typing import TypeAlias

MAX_REPORT_BYTES = 1024 * 1024
MAX_RENDER_WORKERS = 4
ROOT = Path(__file__).resolve().parents[1]
ReportSpec: TypeAlias = tuple[str, str, str]
_BASE_REPORTS: tuple[ReportSpec, ...] = (
    (
        "examples.ci_replay_for_admitted_slice",
        "build_report",
        "tests/golden/frontend/ci_replay_for_admitted_slice_report.json",
    ),
    (
        "examples.oci_source_worker_release_provenance_readiness",
        "build_report",
        "tests/golden/frontend/oci_source_worker_release_provenance_readiness_report.json",
    ),
    (
        "examples.real_triton_first_slice_plan",
        "build_report",
        "tests/golden/frontend/real_triton_first_slice_plan_report.json",
    ),
    (
        "examples.source_ingestion_maintainer_security_review_packet",
        "build_report",
        "tests/golden/frontend/source_ingestion_maintainer_security_review_packet_report.json",
    ),
    (
        "examples.source_ingestion_maintainer_approval_artifact",
        "build_report",
        "tests/golden/frontend/source_ingestion_maintainer_approval_artifact_report.json",
    ),
    (
        "examples.source_ingestion_admission_gate",
        "build_report",
        "tests/golden/frontend/source_ingestion_admission_gate_report.json",
    ),
    (
        "examples.source_ingestion_preclaim_acyclicity_gate",
        "build_report",
        "tests/golden/frontend/source_ingestion_preclaim_acyclicity_gate_report.json",
    ),
    (
        "examples.first_real_triton_kernel_path",
        "build_report",
        "tests/golden/frontend/first_real_triton_kernel_path.json",
    ),
    (
        "examples.real_triton_first_slice_evidence_portfolio",
        "build_report",
        "tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json",
    ),
    (
        "examples.objective_alpha_public_evidence_catalog",
        "build_report",
        "tests/golden/proofs/objective_alpha_public_evidence_catalog.json",
    ),
    (
        "examples.objective_alpha_public_evidence_catalog_admission_gate",
        "build_report",
        "tests/golden/proofs/objective_alpha_public_evidence_catalog_admission_gate.json",
    ),
    (
        "examples.objective_alpha_research_claim",
        "build_report",
        "tests/golden/proofs/objective_alpha_research_claim.json",
    ),
    (
        "examples.objective_alpha_research_claim_gate",
        "build_gate_report",
        "tests/golden/proofs/objective_alpha_research_claim_gate.json",
    ),
)
REPORT_STAGES: tuple[tuple[ReportSpec, ...], ...] = (
    _BASE_REPORTS,
    (
        (
            "examples.objective_alpha_catalog_acyclicity_gate",
            "build_report",
            "tests/golden/proofs/objective_alpha_catalog_acyclicity_gate.json",
        ),
        (
            "examples.research_scope_claim_gate",
            "build_current_research_scope_claim_gate_report_text",
            "tests/golden/proofs/research_scope_claim_gate.json",
        ),
    ),
    (
        (
            "examples.real_triton_first_slice_admission_readiness_gate",
            "build_report",
            "tests/golden/frontend/real_triton_first_slice_admission_readiness_gate_report.json",
        ),
        (
            "examples.evidence_graph_acyclicity_gate",
            "build_report",
            "tests/golden/frontend/evidence_graph_acyclicity_gate_report.json",
        ),
    ),
    (
        (
            "examples.real_triton_first_slice_maintainer_approval_request",
            "build_report",
            "tests/golden/frontend/real_triton_first_slice_maintainer_approval_request_report.json",
        ),
    ),
    (
        (
            "examples.objective_beta_research_claim",
            "build_report",
            "tests/golden/proofs/objective_beta_research_claim.json",
        ),
        (
            "examples.objective_beta_research_claim_gate",
            "build_gate_report",
            "tests/golden/proofs/objective_beta_research_claim_gate.json",
        ),
    ),
    (
        (
            "examples.objective_beta_reproducibility_capsule",
            "build_report",
            "tests/golden/proofs/objective_beta_reproducibility_capsule.json",
        ),
    ),
    (
        (
            "examples.objective_beta_reproducibility_gate",
            "build_report",
            "tests/golden/proofs/objective_beta_reproducibility_gate.json",
        ),
    ),
)
REPORTS: tuple[ReportSpec, ...] = tuple(
    spec for stage in REPORT_STAGES for spec in stage
)


class EvidenceGoldenRefreshError(ValueError):
    """Raised when a bounded evidence golden cannot be checked or refreshed."""


def render_reports() -> dict[str, str]:
    """Render every allowlisted report with bounded process isolation."""

    return _render_specs(REPORTS)


def refresh_reports() -> int:
    """Render and atomically refresh each dependency stage in order."""

    refreshed = 0
    for stage in REPORT_STAGES:
        rendered = _render_specs(stage)
        _write_allowed_reports(
            rendered,
            {relative_path for _, _, relative_path in stage},
        )
        refreshed += len(rendered)
    return refreshed


def _render_specs(specs: tuple[ReportSpec, ...]) -> dict[str, str]:
    for _, _, relative_path in specs:
        _validate_relative_path(relative_path)
    with ProcessPoolExecutor(max_workers=MAX_RENDER_WORKERS) as executor:
        report_pairs = list(executor.map(_render_one, specs))
    rendered = dict(report_pairs)
    if len(rendered) != len(specs):
        raise EvidenceGoldenRefreshError("duplicate report path in allowlist")
    return rendered


def _render_one(spec: ReportSpec) -> tuple[str, str]:
    module_name, function_name, relative_path = spec
    module = importlib.import_module(module_name)
    builder = getattr(module, function_name, None)
    if not callable(builder):
        raise EvidenceGoldenRefreshError(
            f"report builder is not callable: {module_name}.{function_name}"
        )
    return relative_path, _validated_report(builder, relative_path)


def stale_reports(rendered: Mapping[str, str]) -> list[str]:
    """Return allowlisted paths whose checked-in content differs."""

    stale: list[str] = []
    for relative_path, report in rendered.items():
        target = _target_path(relative_path)
        if target.is_symlink() or not target.is_file():
            stale.append(relative_path)
            continue
        if target.read_text(encoding="utf-8") != report:
            stale.append(relative_path)
    return stale


def write_reports(rendered: Mapping[str, str]) -> None:
    """Atomically replace only the allowlisted golden files."""

    expected_paths = {relative_path for _, _, relative_path in REPORTS}
    _write_allowed_reports(rendered, expected_paths)


def _write_allowed_reports(
    rendered: Mapping[str, str],
    expected_paths: set[str],
) -> None:
    allowlisted_paths = {relative_path for _, _, relative_path in REPORTS}
    if not expected_paths or not expected_paths <= allowlisted_paths:
        raise EvidenceGoldenRefreshError("expected report path allowlist mismatch")
    if set(rendered) != expected_paths:
        raise EvidenceGoldenRefreshError("rendered report allowlist mismatch")
    for relative_path, report in rendered.items():
        target = _target_path(relative_path)
        if target.is_symlink():
            raise EvidenceGoldenRefreshError(
                f"refusing to replace symlink: {relative_path}"
            )
        _atomic_write(target, report)


def _validated_report(
    builder: Callable[[], object],
    relative_path: str,
) -> str:
    try:
        report = builder()
    except (MemoryError, RecursionError) as exc:
        raise EvidenceGoldenRefreshError(
            f"report generation failed: {relative_path}"
        ) from exc
    if not isinstance(report, str) or not report.endswith("\n"):
        raise EvidenceGoldenRefreshError(
            f"report must be newline-terminated text: {relative_path}"
        )
    encoded = report.encode("utf-8")
    if len(encoded) > MAX_REPORT_BYTES or b"\x00" in encoded:
        raise EvidenceGoldenRefreshError(f"report bounds rejected: {relative_path}")
    try:
        payload = json.loads(report)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise EvidenceGoldenRefreshError(
            f"report is not valid JSON: {relative_path}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise EvidenceGoldenRefreshError(
            f"report root must be an object: {relative_path}"
        )
    return report


def _validate_relative_path(relative_path: str) -> None:
    path = PurePosixPath(relative_path)
    if (
        path.is_absolute()
        or ".." in path.parts
        or path.suffix != ".json"
        or path.parts[:2] != ("tests", "golden")
    ):
        raise EvidenceGoldenRefreshError(
            f"report path is outside the golden allowlist: {relative_path}"
        )


def _target_path(relative_path: str) -> Path:
    _validate_relative_path(relative_path)
    target = ROOT.joinpath(*PurePosixPath(relative_path).parts)
    if target.parent.resolve() != target.parent or ROOT not in target.parents:
        raise EvidenceGoldenRefreshError(
            f"report parent path rejected: {relative_path}"
        )
    return target


def _atomic_write(target: Path, report: str) -> None:
    target.parent.mkdir(parents=False, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="x",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(report)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="atomically refresh the fixed golden allowlist instead of checking it",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.write:
        refreshed = refresh_reports()
        print(f"refreshed {refreshed} CI-bound evidence goldens")
        return 0
    rendered = render_reports()
    stale = stale_reports(rendered)
    if stale:
        print("stale CI-bound evidence goldens:")
        for relative_path in stale:
            print(relative_path)
        return 1
    print(f"verified {len(rendered)} CI-bound evidence goldens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
