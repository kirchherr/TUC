from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "integration" / "bounded_cpu_model_session_audit" / "audit_receipt.py"
RECEIPT = ROOT / "docs" / "evidence" / "bounded-model-session-36570752112.json"
GOLDEN = ROOT / "tests" / "golden" / "bounded_model_session_audit" / "report.json"
SCHEMA = ROOT / "schemas" / "bounded_model_session_audit_report.v0.schema.json"


def test_audit_matches_golden_under_isolated_python(tmp_path: Path) -> None:
    completed = _run(RECEIPT, cwd=tmp_path)

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout == GOLDEN.read_text(encoding="utf-8")


def test_audit_uses_only_reviewed_stdlib_surface() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )

    assert imported == {
        "__future__",
        "hashlib",
        "json",
        "math",
        "pathlib",
        "struct",
        "sys",
        "typing",
    }
    for forbidden in (
        "import tuc",
        "import numpy",
        "import subprocess",
        "import socket",
        "import ctypes",
        "import importlib",
    ):
        assert forbidden not in source
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"compile", "eval", "exec", "__import__"}
        for node in ast.walk(tree)
    )


def test_audit_schema_is_closed_and_matches_golden() -> None:
    schema = _load(SCHEMA)
    report = _load(GOLDEN)

    assert schema["additionalProperties"] is False
    assert set(cast(list[str], schema["required"])) == set(report)
    properties = cast(dict[str, Any], schema["properties"])
    assert properties["independent_organizational_evidence"]["const"] is False
    assert properties["new_native_execution"]["const"] is False
    assert properties["stdlib_only"]["const"] is True
    assert properties["third_party_dependencies"]["const"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_commit", "0" * 40),
        ("wheel_sha256", "0" * 64),
        ("consumer_sha256", "0" * 64),
    ),
)
def test_audit_rejects_identity_drift_without_disclosure(
    tmp_path: Path, field: str, value: str
) -> None:
    private = tmp_path / "private-receipt.json"
    payload = _load(RECEIPT)
    payload[field] = value
    payload["private_marker"] = "DO_NOT_LOG_THIS"
    private.write_text(json.dumps(payload), encoding="utf-8")

    completed = _run(private, cwd=tmp_path)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "bounded-model-session-audit: input rejected\n"
    assert "DO_NOT_LOG_THIS" not in completed.stderr
    assert str(private) not in completed.stderr


def test_audit_rejects_numerical_drift(tmp_path: Path) -> None:
    private = tmp_path / "receipt.json"
    payload = _load(RECEIPT)
    integration = cast(dict[str, Any], payload["integration"])
    records = cast(list[dict[str, Any]], integration["records"])
    records[0]["outputs"][0] = 99.0
    private.write_text(json.dumps(payload), encoding="utf-8")

    completed = _run(private, cwd=tmp_path)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "bounded-model-session-audit: input rejected\n"


def test_audit_rejects_duplicate_keys(tmp_path: Path) -> None:
    private = tmp_path / "receipt.json"
    private.write_text(
        RECEIPT.read_text(encoding="utf-8").replace(
            '{"consumer_sha256":', '{"consumer_sha256":"duplicate","consumer_sha256":', 1
        ),
        encoding="utf-8",
    )

    completed = _run(private, cwd=tmp_path)

    assert completed.returncode == 2
    assert completed.stderr == "bounded-model-session-audit: input rejected\n"


def test_audit_rejects_oversized_receipt(tmp_path: Path) -> None:
    private = tmp_path / "receipt.json"
    private.write_bytes(b"x" * (16 * 1024 + 1))

    completed = _run(private, cwd=tmp_path)

    assert completed.returncode == 2
    assert completed.stderr == "bounded-model-session-audit: input rejected\n"


@pytest.mark.parametrize("arguments", ([], ["one", "two"]))
def test_audit_rejects_ambiguous_arity(arguments: list[str]) -> None:
    completed = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 2
    assert completed.stderr == "usage: python audit_receipt.py RECEIPT.json\n"


@pytest.mark.parametrize(
    ("path", "marker"),
    (
        (Path("docs/BOUNDED_MODEL_SESSION_AUDIT.md"), "# Bounded Model Session Audit"),
        (
            Path("rfcs/0335-bounded-model-session-audit.md"),
            "# RFC 0335: Bounded Model Session Audit",
        ),
        (Path("README.md"), "reduced-dependency session audit"),
        (Path("ROADMAP.md"), "Bounded Model Session Audit"),
        (Path("TUC_MASTER_PLAN.md"), "bounded model-session audit"),
        (Path("docs/ROADMAP_STATUS.md"), "Bounded Model Session Audit"),
    ),
)
def test_audit_is_bound_into_project_guidance(path: Path, marker: str) -> None:
    assert marker in path.read_text(encoding="utf-8")


def _run(receipt: Path, *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(receipt)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=cwd,
    )


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise TypeError("expected JSON object")
    return cast(dict[str, Any], value)
