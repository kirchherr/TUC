"""Committed source binding, exclusive output and actual isolated offline replay."""

import json
import os
import stat
import subprocess
import sys
import zipfile
from hashlib import sha256
from pathlib import Path

import pytest

from scripts import build_model_application_audit_kit as builder

ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args, data=None):
    return subprocess.run(
        ["git", "-c", f"safe.directory={repo}", "-c", "commit.gpgsign=false",
         "-c", f"core.hooksPath={repo / 'no-hooks'}", "-c", "user.name=Audit kit test",
         "-c", "user.email=audit-kit@example.invalid", "-C", str(repo), *args],
        input=data, capture_output=True, check=True, timeout=15,
    ).stdout


@pytest.fixture
def source_repo(tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()
    (repo / "no-hooks").mkdir()
    git(repo, "init", "--template=")
    for member, relative in builder.SOURCE_FILES.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"committed " + member.encode("ascii"))
    git(repo, "add", "--", *builder.SOURCE_FILES.values())
    git(repo, "commit", "-m", "fixed source fixture")
    return repo


def test_deterministic_committed_kit_and_isolated_actual_replay(tmp_path):
    one, two = tmp_path / "one.zip", tmp_path / "two.zip"
    digest = builder.build_audit_kit(ROOT, one)
    assert builder.build_audit_kit(ROOT, two) == digest == sha256(one.read_bytes()).hexdigest()
    assert one.read_bytes() == two.read_bytes()
    extracted = tmp_path / "offline"
    extracted.mkdir()
    with zipfile.ZipFile(one) as kit:
        assert kit.namelist() == sorted(builder.MEMBERS)
        for info in kit.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_STORED
            assert stat.S_ISREG(info.external_attr >> 16)
            assert not (info.external_attr >> 16) & 0o111
            (extracted / info.filename).write_bytes(kit.read(info))
    expected = "".join(
        f"{sha256((extracted / name).read_bytes()).hexdigest()}  {name}\n"
        for name in sorted(builder.MEMBERS - {"CHECKSUMS.sha256"})
    )
    assert (extracted / "CHECKSUMS.sha256").read_text() == expected
    head = builder._git(ROOT, "rev-parse", "HEAD").decode().strip()
    assert (extracted / "SOURCE.txt").read_text() == f"source_commit={head}\n"
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(extracted / "audit_native_receipt.py"),
         "--ci-packet", str(extracted / "observed-ci-59ad813.json")],
        cwd=extracted, capture_output=True, timeout=30, check=True,
    )
    report = json.loads(result.stdout)
    assert report["status"] == "PASS" and report["scalar_checks"] == 18
    assert report["rejection_checks"] == 4 and report["tuc_imported"] is False
    assert report["native_execution_performed"] is False and result.stderr == b""


def test_working_tree_changes_and_untracked_notes_do_not_enter_kit(source_repo, tmp_path):
    before, after = tmp_path / "before.zip", tmp_path / "after.zip"
    builder.build_audit_kit(source_repo, before)
    for relative in builder.SOURCE_FILES.values():
        (source_repo / relative).write_bytes(b"uncommitted replacement")
    (source_repo / "HANDOFF.md").write_bytes(b"private notes")
    builder.build_audit_kit(source_repo, after)
    assert before.read_bytes() == after.read_bytes()


def test_packaging_never_executes_committed_auditor(source_repo, tmp_path):
    marker = tmp_path / "must-not-exist"
    path = source_repo / builder.SOURCE_FILES["audit_native_receipt.py"]
    path.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n")
    git(source_repo, "add", "--", builder.SOURCE_FILES["audit_native_receipt.py"])
    git(source_repo, "commit", "-m", "inert source sentinel")
    builder.build_audit_kit(source_repo, tmp_path / "inert.zip")
    assert not marker.exists()


@pytest.mark.parametrize("mode", ["120000", "160000"])
def test_committed_symlink_and_submodule_reject(source_repo, tmp_path, mode):
    oid = (
        git(source_repo, "hash-object", "-w", "--stdin", data=b"outside-target\n")
        if mode == "120000" else git(source_repo, "rev-parse", "HEAD")
    ).decode().strip()
    path = builder.SOURCE_FILES["audit_native_receipt.py"]
    git(source_repo, "update-index", "--cacheinfo", f"{mode},{oid},{path}")
    git(source_repo, "commit", "-m", "nonregular source fixture")
    output = tmp_path / "rejected.zip"
    with pytest.raises(builder.AuditKitError, match="^model_application_audit_kit_rejected$"):
        builder.build_audit_kit(source_repo, output)
    assert not output.exists()


def test_missing_committed_file_does_not_fall_back_to_worktree(source_repo, tmp_path):
    git(source_repo, "rm", "--cached", "--", builder.SOURCE_FILES["observed-ci-59ad813.json"])
    git(source_repo, "commit", "-m", "missing committed source")
    output = tmp_path / "missing.zip"
    with pytest.raises(builder.AuditKitError):
        builder.build_audit_kit(source_repo, output)
    assert not output.exists()


def test_oversized_blob_rejects_before_reading_body(source_repo, tmp_path, monkeypatch):
    path = builder.SOURCE_FILES["audit_native_receipt.py"]
    (source_repo / path).write_bytes(b"x" * (builder.MAX_SOURCE_BYTES + 1))
    git(source_repo, "add", "--", path)
    git(source_repo, "commit", "-m", "oversized source")
    original = builder._git
    bodies = []

    def observe(repo, *args):
        if args[:2] == ("cat-file", "blob"):
            bodies.append(args)
        return original(repo, *args)

    monkeypatch.setattr(builder, "_git", observe)
    with pytest.raises(builder.AuditKitError):
        builder.build_audit_kit(source_repo, tmp_path / "large.zip")
    assert not bodies


def test_existing_output_is_preserved(source_repo, tmp_path):
    output = tmp_path / "existing.zip"
    output.write_bytes(b"keep existing artifact")
    with pytest.raises(builder.AuditKitError):
        builder.build_audit_kit(source_repo, output)
    assert output.read_bytes() == b"keep existing artifact"


@pytest.mark.parametrize("name", ["report.txt", ".zip", "bad\nname.zip", "bad\u2603.zip"])
def test_output_name_cannot_spoof_checksum_line(source_repo, tmp_path, name):
    with pytest.raises(builder.AuditKitError):
        builder.build_audit_kit(source_repo, tmp_path / name)


def test_inherited_git_directory_cannot_replace_source(source_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "absent"))
    output = tmp_path / "environment.zip"
    builder.build_audit_kit(source_repo, output)
    with zipfile.ZipFile(output) as kit:
        assert kit.read("SOURCE.txt").startswith(b"source_commit=")


def test_checkout_program_named_git_cannot_be_executed(source_repo, tmp_path, monkeypatch):
    shadow = source_repo / ("git.exe" if os.name == "nt" else "git")
    shadow.write_bytes(b"#!/bin/sh\nexit 99\n")
    shadow.chmod(0o755)
    monkeypatch.setenv("PATH", str(source_repo) + os.pathsep + os.environ.get("PATH", ""))
    program = Path(builder._git_executable(source_repo))
    assert program.is_absolute() and not program.is_relative_to(source_repo)
    builder.build_audit_kit(source_repo, tmp_path / "no-shadow.zip")


def test_git_replacement_objects_cannot_relabel_packaged_source(source_repo, tmp_path, monkeypatch):
    monkeypatch.delenv("GIT_NO_REPLACE_OBJECTS", raising=False)
    first, second = tmp_path / "original.zip", tmp_path / "replacement.zip"
    builder.build_audit_kit(source_repo, first)
    original = git(source_repo, "rev-parse", "HEAD").decode().strip()
    path = builder.SOURCE_FILES["audit_native_receipt.py"]
    (source_repo / path).write_bytes(b"replacement object payload")
    git(source_repo, "add", "--", path)
    git(source_repo, "commit", "-m", "replacement payload")
    replacement = git(source_repo, "rev-parse", "HEAD").decode().strip()
    git(source_repo, "replace", original, replacement)
    git(source_repo, "update-ref", "HEAD", original)
    assert git(source_repo, "show", f"HEAD:{path}") == b"replacement object payload"
    builder.build_audit_kit(source_repo, second)
    assert first.read_bytes() == second.read_bytes()


def test_exclusive_output_creation_closes_check_write_race(source_repo, tmp_path, monkeypatch):
    original = builder._snapshot
    output = tmp_path / "race.zip"

    def race(repo):
        result = original(repo)
        output.write_bytes(b"another writer")
        return result

    monkeypatch.setattr(builder, "_snapshot", race)
    with pytest.raises(builder.AuditKitError):
        builder.build_audit_kit(source_repo, output)
    assert output.read_bytes() == b"another writer"


def test_cli_runs_with_standard_library_outside_checkout(tmp_path):
    output = tmp_path / "cli.zip"
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(ROOT / "scripts/build_model_application_audit_kit.py"),
         "--output", str(output)],
        cwd=tmp_path, capture_output=True, timeout=30, check=True,
    )
    assert result.stdout.decode().strip() == f"{sha256(output.read_bytes()).hexdigest()}  cli.zip"
    assert result.stderr == b""


def test_cli_rejection_is_closed_and_publishes_no_checksum(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(ROOT / "scripts/build_model_application_audit_kit.py"),
         "--output", str(tmp_path / "absent" / "rejected.zip")],
        cwd=tmp_path, capture_output=True, timeout=30, check=False,
    )
    assert result.returncode == 2 and result.stdout == b""
    assert result.stderr.decode().strip() == "model_application_audit_kit_rejected"


def test_output_symlink_is_never_followed(source_repo, tmp_path):
    target, output = tmp_path / "preserve", tmp_path / "link.zip"
    target.write_bytes(b"preserve")
    try:
        os.symlink(target, output)
    except OSError:
        pytest.skip("host does not permit test symlinks")
    with pytest.raises(builder.AuditKitError):
        builder.build_audit_kit(source_repo, output)
    assert target.read_bytes() == b"preserve"
