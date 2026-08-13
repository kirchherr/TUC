from __future__ import annotations

import json

import pytest

from tuc.report_output import (
    MAX_PUBLIC_REPORT_BYTES,
    PublicReportOutputError,
    emit_public_json_report,
    emit_public_text_report,
)


def _report(payload: object) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def test_public_report_emitter_preserves_valid_output(capfd: pytest.CaptureFixture[str]) -> None:
    report = _report(
        {
            "artifact_digest": "sha256:" + "a" * 64,
            "long_lived_signing_secret_required": False,
            "schema_version": "tuc.public_report.test.v0",
            "source_text": False,
            "status": "PASS",
        }
    )

    emit_public_json_report(report)

    assert capfd.readouterr().out == report


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"password": "value"}, "sensitive field"),
        ({"nested": {"access_token": "value"}}, "sensitive field"),
        ({"source_text": "print('payload')"}, "raw field"),
        ({"runtime_handles": ["handle"]}, "raw field"),
        ({"path": "/home/user/private"}, "absolute path"),
        ({"value": "github_pat_" + "a" * 24}, "secret material"),
        ({"value": "-----BEGIN PRIVATE KEY-----"}, "secret material"),
    ],
)
def test_public_report_emitter_rejects_sensitive_payloads(
    payload: object,
    message: str,
) -> None:
    with pytest.raises(PublicReportOutputError, match=message):
        emit_public_json_report(_report(payload))


@pytest.mark.parametrize(
    "report",
    [
        "",
        "[]\n",
        "{\"status\": \"PASS\"}",
        "{\"status\": NaN}\n",
        "{\"status\": 1, \"status\": 2}\n",
        "{not-json}\n",
    ],
)
def test_public_report_emitter_rejects_invalid_contracts(report: str) -> None:
    with pytest.raises(PublicReportOutputError):
        emit_public_json_report(report)


def test_public_report_emitter_rejects_oversized_input() -> None:
    report = '{"value":"' + ("x" * MAX_PUBLIC_REPORT_BYTES) + '"}\n'

    with pytest.raises(PublicReportOutputError, match="byte limit"):
        emit_public_json_report(report)


def test_public_report_emitter_rejects_excessive_depth() -> None:
    payload: object = "value"
    for _ in range(34):
        payload = {"nested": payload}

    with pytest.raises(PublicReportOutputError, match="nesting limit"):
        emit_public_json_report(_report(payload))


def test_public_text_report_emitter_preserves_valid_output(
    capfd: pytest.CaptureFixture[str],
) -> None:
    report = (
        "tuc.evidence @example {\n"
        '  trusted_executor_registry = "trusted_runtime_executor_registry.v0"\n'
        '  status = "passed"\n'
        "}\n"
    )

    emit_public_text_report(report)

    assert capfd.readouterr().out == report


@pytest.mark.parametrize(
    "report",
    [
        'gate { password = "value" }\n',
        'gate { source_text = "print(1)" }\n',
        'gate { host_path = "C:\\\\private" }\n',
        "gate { value = \"github_pat_" + "a" * 24 + "\" }\n",
        "gate { value = \"-----BEGIN PRIVATE KEY-----\" }\n",
        "gate { status = \"passed\" }",
        "gate { status = \"passed\" }\r\n",
        "gate { status = \"passed\" }\x00\n",
    ],
)
def test_public_text_report_emitter_rejects_unsafe_reports(report: str) -> None:
    with pytest.raises(PublicReportOutputError):
        emit_public_text_report(report)
