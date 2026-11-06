"""Adversarial receipt and committed source controls for the operator procedure."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from scripts import reproduce_model_application as operator

ROOT = Path(__file__).resolve().parents[1]
OBSERVED = ROOT / operator.CLIENT / "observed-ci-59ad813.json"
RECORD_DIGEST = "6a77307516b633d45b45f8efa4581076c854549491960652026b7219a3ff8bd8"


def observation(source: str, files: dict[str, bytes]) -> dict[str, Any]:
    packet = json.loads(OBSERVED.read_bytes())
    packet.update(
        source_commit=source,
        wheel_sha256="b" * 64,
        consumer_sha256=sha256(files[operator.CONSUMER]).hexdigest(),
        audit_sha256=sha256(files[operator.AUDITOR]).hexdigest(),
    )
    return {
        "schema_version": operator.SCHEMA, "packet": packet,
        "environment": {"system": "Linux", "machine": "x86_64", "python": "3.12.13"},
        "completed_steps": list(operator.STEPS),
        "requirements_sha256": sha256(files[operator.LOCK]).hexdigest(),
        "external_origin_verified": False,
    }


@pytest.fixture(scope="module")
def source() -> tuple[str, dict[str, bytes]]:
    revision = operator._git(ROOT, "rev-parse", "HEAD").decode("ascii").strip()
    return revision, operator._snapshot(ROOT, revision, build=False)


def test_review_cli_uses_committed_auditor_outside_checkout(
    tmp_path: Path, source: tuple[str, dict[str, bytes]],
) -> None:
    revision, files = source
    record = tmp_path / "observation.json"
    record.write_bytes(operator.encoded(observation(revision, files)))
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(ROOT / "scripts/reproduce_model_application.py"),
         "verify", "--source-commit", revision, str(record), "--expected-wheel-sha256", "b" * 64],
        cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path)}, capture_output=True,
        timeout=60, check=True,
    )
    assert not result.stderr
    report = json.loads(result.stdout)
    assert report["record_sha256"] == RECORD_DIGEST
    assert report["scalar_checks"] == 18 and report["rejection_checks"] == 4
    assert report["external_origin_verified"] is False
    assert report["native_execution_performed"] is False


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("packet", "source_commit"), "a" * 40),
        (("packet", "consumer_sha256"), "1" * 64),
        (("packet", "audit_sha256"), "2" * 64),
        (("packet", "wheel_sha256"), "missing"),
        (("requirements_sha256",), "3" * 64),
        (("external_origin_verified",), True),
        (("completed_steps",), ["snapshot", "native_run"]),
        (("environment", "python"), "3.15.1"),
        (("environment", "machine"), "aarch64"),
        (("environment", "shell"), "cat /etc/passwd"),
        (("packet", "audit", "scalar_checks"), 17),
        (("packet", "integration", "workspaces_clean"), False),
    ],
)
def test_untrusted_context_or_result_drift_rejected(
    source: tuple[str, dict[str, bytes]], path: tuple[str, ...], value: object,
) -> None:
    revision, files = source
    payload = observation(revision, files)
    target = payload
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = value
    with pytest.raises(operator.ReproductionRejected):
        operator.verify(operator.encoded(payload), commit=revision, files=files)


def test_no_duplicate_fields_or_oversized_observations(
    source: tuple[str, dict[str, bytes]],
) -> None:
    revision, files = source
    valid = operator.encoded(observation(revision, files))
    with pytest.raises(operator.ReproductionRejected, match="packet_shape"):
        operator.verify(
            b'{"external_origin_verified":true,' + valid[1:], commit=revision, files=files,
        )
    with pytest.raises(operator.ReproductionRejected, match="packet_budget"):
        operator.verify(valid + b" " * operator.MAX_PACKET, commit=revision, files=files)
    with pytest.raises(operator.ReproductionRejected, match="packet_binding"):
        operator.verify(valid, commit=revision, files=files, expected_wheel="c" * 64)


def _small_repo(path: Path) -> tuple[Path, str]:
    repo = path / "repo"
    repo.mkdir()
    operator._git(repo, "init", "-q")
    for name in (*operator.BUILD_FILES, "src/tuc/__init__.py"):
        file = repo / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"trusted committed bytes\n")
    operator._git(repo, "add", ".")
    operator._git(repo, "-c", "user.name=TUC test", "-c", "user.email=test@example.invalid",
                  "-c", "core.hooksPath=.git/no-hooks", "-c", "commit.gpgSign=false",
                  "commit", "-qm", "fixed source")
    return repo, operator._git(repo, "rev-parse", "HEAD").decode("ascii").strip()


def test_build_snapshot_excludes_dirty_code_and_private_notes(tmp_path: Path) -> None:
    repo, revision = _small_repo(tmp_path)
    (repo / "src/tuc/__init__.py").write_bytes(b"raise SystemExit(8)\n")
    (repo / "src/tuc/untracked.py").write_bytes(b"untracked executable\n")
    (repo / "HANDOFF.md").write_bytes(b"private note\n")
    result = operator._snapshot(repo, revision, build=True)
    assert result["src/tuc/__init__.py"] == b"trusted committed bytes\n"
    assert set(result) == {*operator.BUILD_FILES, "src/tuc/__init__.py"}
    with pytest.raises(operator.ReproductionRejected, match="source_revision"):
        operator._snapshot(repo, "9" * 40, build=True)


def test_committed_link_rejected_before_build(tmp_path: Path) -> None:
    repo, _ = _small_repo(tmp_path)
    oid = operator._git(repo, "hash-object", "-w", operator.LOCK).decode("ascii").strip()
    operator._git(repo, "update-index", "--add", "--cacheinfo", f"120000,{oid},src/tuc/link.py")
    operator._git(repo, "-c", "user.name=TUC test", "-c", "user.email=test@example.invalid",
                  "-c", "core.hooksPath=.git/no-hooks", "-c", "commit.gpgSign=false",
                  "commit", "-qm", "committed hostile link")
    revision = operator._git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    with pytest.raises(operator.ReproductionRejected, match="source_file_type"):
        operator._snapshot(repo, revision, build=True)


def test_output_is_exclusive_and_never_inside_checkout(tmp_path: Path) -> None:
    repo = (tmp_path / "checkout").resolve()
    repo.mkdir()
    with pytest.raises(operator.ReproductionRejected, match="output_boundary"):
        operator._output(repo, repo / "capture")
    output = operator._output(repo, tmp_path / "fresh")
    existing = output / "previous-result"
    existing.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        operator._output(repo, output)
    assert existing.read_bytes() == b"keep"
