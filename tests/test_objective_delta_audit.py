from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = PROJECT_ROOT / "integration" / "objective_delta"
AUDIT_ROOT = PROJECT_ROOT / "integration" / "objective_delta_audit"
SCRIPT_PATH = AUDIT_ROOT / "audit_reproducer.py"
VECTOR_PATH = AUDIT_ROOT / "conformance_vector.v0.json"
REPORT_GOLDEN = PROJECT_ROOT / "tests" / "golden" / "objective_delta_audit" / "report.json"
REPORT_SCHEMA = PROJECT_ROOT / "schemas" / "objective_delta_audit_report.v0.schema.json"
VECTOR_SCHEMA = PROJECT_ROOT / "schemas" / "objective_delta_conformance_vector.v0.schema.json"


def test_objective_delta_audit_matches_golden_in_isolated_python(tmp_path: Path) -> None:
    completed = _run_audit(CONTRACT_ROOT, VECTOR_PATH, cwd=tmp_path)

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout == REPORT_GOLDEN.read_text(encoding="utf-8")


def test_objective_delta_audit_uses_only_audited_stdlib_surface() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )

    assert imported_roots == {
        "__future__",
        "hashlib",
        "json",
        "math",
        "pathlib",
        "sys",
        "typing",
    }
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"compile", "eval", "exec", "__import__"}
        for node in ast.walk(tree)
    )
    for forbidden in (
        "import tuc",
        "import numpy",
        "import subprocess",
        "import socket",
        "import ctypes",
        "import importlib",
    ):
        assert forbidden not in source


def test_objective_delta_audit_schemas_are_closed_and_match_artifacts() -> None:
    report_schema = _load_json(REPORT_SCHEMA)
    vector_schema = _load_json(VECTOR_SCHEMA)
    report = _load_json(REPORT_GOLDEN)
    vector = _load_json(VECTOR_PATH)

    assert report_schema["additionalProperties"] is False
    assert vector_schema["additionalProperties"] is False
    assert set(cast(list[str], report_schema["required"])) == set(report)
    assert set(cast(list[str], vector_schema["required"])) == set(vector)
    assert report_schema["properties"]["independent_organizational_evidence"][
        "const"
    ] is False
    assert report_schema["properties"]["native_backend_execution"]["const"] is False
    assert report_schema["properties"]["python_code_executed"]["const"] is True
    assert report_schema["properties"]["raw_tensor_values_serialized"]["const"] is False
    assert report_schema["properties"]["stdlib_only"]["const"] is True
    assert report_schema["properties"]["third_party_dependencies"]["const"] is False


def test_objective_delta_audit_vector_publishes_exact_fixed_semantics() -> None:
    vector = _load_json(VECTOR_PATH)

    assert vector["inputs"] == {
        "lhs": [[1.0, -2.0], [0.5, 3.0]],
        "rhs": [[2.0, 1.0], [-1.0, 0.25]],
    }
    assert vector["elementwise_semantics"] == "identity"
    assert vector["expected_public_outputs"] == {
        "api_activated": [[4.0, 0.5], [-2.0, 1.25]],
    }


def test_objective_delta_audit_rejects_package_drift_without_disclosure(
    tmp_path: Path,
) -> None:
    contract = tmp_path / "private-contract"
    shutil.copytree(CONTRACT_ROOT, contract)
    private = contract / "external_vector.v0.json"
    payload = _load_json(private)
    payload["secret"] = "DO_NOT_LOG_THIS"
    private.write_text(json.dumps(payload), encoding="utf-8")

    completed = _run_audit(contract, VECTOR_PATH, cwd=tmp_path)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "objective-delta-audit: input rejected\n"
    assert str(private) not in completed.stderr
    assert "DO_NOT_LOG_THIS" not in completed.stderr


def test_objective_delta_audit_rejects_duplicate_json_key(tmp_path: Path) -> None:
    contract = tmp_path / "contract"
    shutil.copytree(CONTRACT_ROOT, contract)
    source = contract / "source_intent.v0.json"
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            '{\n  "name":',
            '{\n  "name": "duplicate",\n  "name":',
            1,
        ),
        encoding="utf-8",
    )

    completed = _run_audit(contract, VECTOR_PATH, cwd=tmp_path)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "objective-delta-audit: input rejected\n"


def test_objective_delta_audit_rejects_conformance_case_drift(tmp_path: Path) -> None:
    contract = tmp_path / "contract"
    shutil.copytree(CONTRACT_ROOT, contract)
    package = contract / "external_systolic.v0.json"
    payload = _load_json(package)
    payload["conformance_cases"][0]["expected_supported"] = False
    package.write_text(json.dumps(payload), encoding="utf-8")

    completed = _run_audit(contract, VECTOR_PATH, cwd=tmp_path)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "objective-delta-audit: input rejected\n"


def test_objective_delta_audit_rejects_oversized_input(tmp_path: Path) -> None:
    contract = tmp_path / "contract"
    shutil.copytree(CONTRACT_ROOT, contract)
    source = contract / "source_intent.v0.json"
    source.write_bytes(b"x" * (16 * 1024 + 1))

    completed = _run_audit(contract, VECTOR_PATH, cwd=tmp_path)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "objective-delta-audit: input rejected\n"


@pytest.mark.parametrize("arguments", ([], ["one"], ["one", "two", "three"]))
def test_objective_delta_audit_rejects_ambiguous_arity(arguments: list[str]) -> None:
    completed = subprocess.run(
        [sys.executable, "-I", str(SCRIPT_PATH), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "usage: python audit_reproducer.py CONTRACT_DIR CONFORMANCE_VECTOR.json\n"
    )


@pytest.mark.parametrize(
    ("path", "marker"),
    (
        (
            Path("docs/OBJECTIVE_DELTA_AUDIT_PATH.md"),
            "# Objective Delta Reduced-Dependency Audit Path",
        ),
        (
            Path("rfcs/0294-objective-delta-reduced-dependency-audit-path.md"),
            "# RFC 0294: Objective Delta Reduced-Dependency Audit Path",
        ),
        (Path("README.md"), "Objective Delta Reduced-Dependency Audit Path"),
        (Path("ROADMAP.md"), "reduced-dependency audit path"),
        (Path("TUC_MASTER_PLAN.md"), "reduced-dependency audit path"),
        (Path("docs/ROADMAP_STATUS.md"), "Reduced-Dependency Audit Path"),
    ),
)
def test_objective_delta_audit_is_bound_into_project_guidance(
    path: Path,
    marker: str,
) -> None:
    assert marker in path.read_text(encoding="utf-8")


def _run_audit(
    contract_root: Path,
    vector_path: Path,
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            str(SCRIPT_PATH),
            str(contract_root),
            str(vector_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=cwd,
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if type(payload) is not dict:
        raise TypeError("expected JSON object")
    return cast(dict[str, Any], payload)
