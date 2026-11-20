"""Returned observations must remain bounded data, even when internally consistent."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from scripts import audit_supplied_model_candidate as verifier

ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / "docs/evidence/research-candidate-fdfcc19/supplied-wheel"


@pytest.fixture
def packet(tmp_path: Path) -> Path:
    root = tmp_path / "returned"
    for name in verifier.FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((RETAINED / name).read_bytes())
    return root


@pytest.fixture
def no_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("malformed packet reached numerical subprocess")

    monkeypatch.setattr(verifier.subprocess, "run", forbidden)


def rewrite(root: Path, name: str, field: str, value: object) -> None:
    path = root / name
    record = json.loads(path.read_bytes())
    record[field] = value
    path.write_bytes(verifier.encoded(record))


def test_actual_retained_packet_reruns_only_pinned_stdlib_auditor(
    packet: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    run = subprocess.run
    marker = packet / "executed.txt"
    # An operator-supplied Python file must never become the numerical auditor.
    (packet / "audit_native_receipt.py").write_text(
        "raise AssertionError('returned code executed')", encoding="ascii",
    )

    def observed(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        assert command[:3] == [sys.executable, "-I", "-S"]
        script = Path(command[3])
        assert not script.is_relative_to(packet)
        assert sha256(script.read_bytes()).hexdigest() == verifier.MATERIALS[verifier.AUDITOR]
        assert kwargs["cwd"] == script.parent
        assert "PYTHONPATH" not in kwargs["env"]
        calls.append(command)
        return run(command, **kwargs)

    monkeypatch.setattr(verifier.subprocess, "run", observed)
    result = verifier.audit(packet)
    assert len(calls) == 3
    assert result["status"] == "PASS"
    assert result["scope"] == "fixed_candidate_record_consistency"
    assert result["source_commit"] == verifier.SOURCE
    assert result["supplied_wheel_sha256"] == verifier.WHEEL
    assert result["input_sha256"] == {
        name: sha256((packet / name).read_bytes()).hexdigest() for name in verifier.FILES
    }
    assert all(r["scalar_checks"] == 18 and r["rejection_checks"] == 4
               for r in result["numerical_audits"].values())
    assert all(result[key] is False for key in (
        "tuc_imported", "native_execution_performed", "external_origin_verified",
        "independent_operator_acceptance",
    ))
    assert not marker.exists()


@pytest.mark.parametrize(("field", "value"), (
    ("source_commit", "0" * 40), ("supplied_wheel_sha256", "0" * 64),
    ("procedure_sha256", "0" * 64), ("requirements_sha256", "0" * 64),
    ("source_material_sha256", {}), ("candidate_run_id", 43826307480),
    ("completed_steps", []), ("tuc_wheel_rebuilt", True),
    ("external_origin_verified", True), ("independent_operator_acceptance", True),
    ("unreviewed_extension", "data"),
))
def test_self_consistent_claims_cannot_change_candidate_or_grant_acceptance(
    packet: Path, no_execution: None, field: str, value: object,
) -> None:
    rewrite(packet, "rehearsal.json", field, value)
    with pytest.raises(verifier.PacketRejected, match="^packet_binding$"):
        verifier.audit(packet)


@pytest.mark.parametrize("field", (
    "source_commit", "wheel_sha256", "consumer_sha256", "audit_sha256",
))
def test_arithmetic_envelope_alone_does_not_authenticate_candidate(
    packet: Path, no_execution: None, field: str,
) -> None:
    rewrite(packet, "session/ci-record.json", field, "0" * (40 if field == "source_commit" else 64))
    with pytest.raises(verifier.PacketRejected, match="^packet_binding$"):
        verifier.audit(packet)


@pytest.mark.parametrize(("group", "field", "value"), (
    ("session", "closed_session_rejections", True),
    ("session", "docker_builds", 1), ("session", "sequences", [1, 2, 3]),
    ("cli", "rejected_commands", 6), ("cli", "installed_outside_checkout", False),
    ("cli", "single_sequence", True),
))
def test_matching_envelope_and_lifecycle_lies_still_reject(
    packet: Path, no_execution: None, group: str, field: str, value: object,
) -> None:
    name = f"{group}/{group}-observation.json"
    rewrite(packet, name, field, value)
    envelope = json.loads((packet / "rehearsal.json").read_bytes())
    envelope["observations"][group][field] = value
    (packet / "rehearsal.json").write_bytes(verifier.encoded(envelope))
    with pytest.raises(verifier.PacketRejected, match="^packet_binding$"):
        verifier.audit(packet)


@pytest.mark.parametrize(("field", "value"), (
    ("docker_cgroup_version", "1"), ("system", "Windows"),
    ("machine", "aarch64"), ("python", "3.13.1"), ("docker_kernel", "\n"),
))
def test_unsupported_or_malformed_environment_claims_reject(
    packet: Path, no_execution: None, field: str, value: str,
) -> None:
    envelope = json.loads((packet / "rehearsal.json").read_bytes())
    envelope["environment"][field] = value
    (packet / "rehearsal.json").write_bytes(verifier.encoded(envelope))
    with pytest.raises(verifier.PacketRejected, match="^environment_claim$"):
        verifier.audit(packet)


@pytest.mark.parametrize("data", (
    b'{"status":"PASS","status":"PASS"}', b'{"value":NaN}', b'{"value":1.0}',
    b'{"value":1000000000000000}', b'{"value":' + b'[' * 13 + b'0' + b']' * 13 + b'}',
    b'\xff', b'[]', b'{}' + b' ' * verifier.MAX_BYTES,
), ids=("duplicate", "nonfinite", "float", "integer", "depth", "encoding", "array", "size"))
def test_json_resource_and_ambiguity_boundaries(data: bytes) -> None:
    with pytest.raises(verifier.PacketRejected, match="^json_boundary$"):
        verifier.read_json(data)


def test_changed_record_rejects_before_auditor(packet: Path, no_execution: None) -> None:
    rewrite(packet, "core/record.json", "workspaces_clean", False)
    with pytest.raises(verifier.PacketRejected, match="^record_digest$"):
        verifier.audit(packet)


def test_forged_audit_cannot_pass_the_actual_numerical_verifier(packet: Path) -> None:
    envelope = json.loads((packet / "rehearsal.json").read_bytes())
    report = envelope["audits"]["core"]
    report["scalar_checks"] = 17
    (packet / "core/audit.json").write_bytes(verifier.encoded(report))
    rewrite(packet, "core/ci-record.json", "audit", report)
    (packet / "rehearsal.json").write_bytes(verifier.encoded(envelope))
    with pytest.raises(verifier.PacketRejected, match="^numerical_audit$"):
        verifier.audit(packet)


def test_local_auditor_drift_cannot_execute(
    packet: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_execution: None,
) -> None:
    changed = tmp_path / "auditor.py"
    changed.write_bytes(b"raise AssertionError('changed local auditor executed')")
    monkeypatch.setattr(verifier, "TRUSTED_AUDITOR", changed)
    with pytest.raises(verifier.PacketRejected, match="^trusted_auditor_digest$"):
        verifier.audit(packet)


@pytest.mark.parametrize("kind", ("missing", "directory", "empty", "oversized"))
def test_invalid_member_rejects_before_execution(
    packet: Path, no_execution: None, kind: str,
) -> None:
    path = packet / "cli/audit.json"
    path.unlink()
    if kind == "directory":
        path.mkdir()
    elif kind == "empty":
        path.write_bytes(b"")
    elif kind == "oversized":
        path.write_bytes(b"x" * (verifier.MAX_BYTES + 1))
    with pytest.raises(verifier.PacketRejected, match="^file_boundary$"):
        verifier.audit(packet)


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink boundary")
@pytest.mark.parametrize("kind", ("member", "parent"))
def test_symlink_redirects_reject(
    packet: Path, tmp_path: Path, no_execution: None, kind: str,
) -> None:
    original = packet / ("cli" if kind == "parent" else "cli/audit.json")
    target = tmp_path / "redirected"
    original.rename(target)
    original.symlink_to(target, target_is_directory=kind == "parent")
    with pytest.raises(verifier.PacketRejected, match="^file_boundary$"):
        verifier.audit(packet)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX fifo boundary")
def test_fifo_does_not_wait_for_a_writer(packet: Path, no_execution: None) -> None:
    path = packet / "core/record.json"
    path.unlink()
    os.mkfifo(path)
    with pytest.raises(verifier.PacketRejected, match="^file_boundary$"):
        verifier.audit(packet)


def test_cli_emits_rejection_without_echoing_operator_paths(packet: Path) -> None:
    (packet / "rehearsal.json").write_bytes(b"not json")
    process = subprocess.run(
        [sys.executable, "-I", "-S", str(ROOT / "scripts/audit_supplied_model_candidate.py"),
         str(packet)], capture_output=True, check=False, timeout=15,
    )
    assert process.returncode == 1
    assert json.loads(process.stdout) == {"status": "REJECTED", "reason": "json_boundary"}
    assert process.stdout.endswith(b"\n") and b"\r" not in process.stdout
    assert not process.stderr
