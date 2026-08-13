from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

import scripts.refresh_ci_bound_evidence_goldens as refresh


def test_report_allowlist_is_fixed_unique_and_bounded() -> None:
    paths = [relative_path for _, _, relative_path in refresh.REPORTS]

    assert len(paths) == 22
    assert len(set(paths)) == len(paths)
    assert len(refresh.REPORT_STAGES) == 7
    assert tuple(
        spec for stage in refresh.REPORT_STAGES for spec in stage
    ) == refresh.REPORTS
    assert all(module.startswith("examples.") for module, _, _ in refresh.REPORTS)
    assert all(
        function
        in {
            "build_report",
            "build_gate_report",
            "build_current_research_scope_claim_gate_report_text",
        }
        for _, function, _ in refresh.REPORTS
    )
    assert all(PurePosixPath(path).parts[:2] == ("tests", "golden") for path in paths)
    assert all(PurePosixPath(path).suffix == ".json" for path in paths)


@pytest.mark.parametrize(
    "relative_path",
    (
        "/tmp/report.json",
        "../report.json",
        "tests/../report.json",
        "tests/golden/report.txt",
        "docs/report.json",
    ),
)
def test_report_path_validation_rejects_escape(relative_path: str) -> None:
    with pytest.raises(refresh.EvidenceGoldenRefreshError, match="outside"):
        refresh._validate_relative_path(relative_path)


def test_report_validation_accepts_bounded_json_object() -> None:
    report = '{"status":"PASS"}\n'

    assert refresh._validated_report(lambda: report, "tests/golden/report.json") == report


@pytest.mark.parametrize(
    ("builder", "message"),
    (
        (lambda: {"status": "PASS"}, "newline-terminated"),
        (lambda: '{"status":"PASS"}', "newline-terminated"),
        (lambda: "not-json\n", "valid JSON"),
        (lambda: "[]\n", "root must be an object"),
        (lambda: '{"value":"\x00"}\n', "bounds rejected"),
        (lambda: "{" + '"value":"' + "x" * refresh.MAX_REPORT_BYTES + '"}\n', "bounds rejected"),
    ),
)
def test_report_validation_fails_closed(
    builder: object,
    message: str,
) -> None:
    assert callable(builder)
    with pytest.raises(refresh.EvidenceGoldenRefreshError, match=message):
        refresh._validated_report(builder, "tests/golden/report.json")


def test_atomic_write_replaces_file_with_utf8_lf(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    target.write_bytes(b"old\r\n")

    refresh._atomic_write(target, '{"status":"PASS"}\n')

    assert target.read_bytes() == b'{"status":"PASS"}\n'
    assert list(tmp_path.glob(".report.json.*.tmp")) == []


def test_write_reports_rejects_incomplete_allowlist() -> None:
    with pytest.raises(refresh.EvidenceGoldenRefreshError, match="allowlist mismatch"):
        refresh.write_reports({})
