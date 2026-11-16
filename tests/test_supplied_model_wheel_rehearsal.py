"""Supplied-wheel tampering must reject before native or installation authority."""

from __future__ import annotations

import json
import os
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from scripts import rehearse_supplied_model_wheel as rehearsal


def test_rehearsal_pin_matches_verified_protected_candidate() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "docs/evidence/research-candidate-fdfcc19/candidate-artifacts.json"
    candidate = json.loads(path.read_bytes())
    assert candidate["status"] == "PASS"
    assert candidate["source"] == rehearsal.SOURCE
    assert candidate["workflow_run"] == rehearsal.CANDIDATE_RUN_ID
    assert candidate["checksums"][rehearsal.WHEEL_NAME] == rehearsal.WHEEL_SHA256
    assert len(rehearsal.WHEEL_SHA256) == 64


def test_changed_supplied_wheel_rejects_before_git_or_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    wheel = tmp_path / rehearsal.WHEEL_NAME
    wheel.write_bytes(b"a changed distribution must not be installed")
    output = tmp_path / "observation"
    monkeypatch.setattr(rehearsal.platform, "system", lambda: "Linux")
    monkeypatch.setattr(rehearsal.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(sys, "version_info", (3, 12, 0))

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("subprocess authority reached before wheel authentication")

    monkeypatch.setattr(rehearsal.subprocess, "run", forbidden)
    with pytest.raises(rehearsal.RehearsalRejected, match="^wheel_digest$"):
        rehearsal.rehearse(tmp_path / "repo", wheel, output)
    assert not output.exists()
    assert list(tmp_path.iterdir()) == [wheel]


def test_authentication_reads_exact_bytes_without_importing_distribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    wheel = tmp_path / rehearsal.WHEEL_NAME
    data = b"unit fixture, deliberately not an executable wheel"
    wheel.write_bytes(data)
    monkeypatch.setattr(rehearsal, "WHEEL_SHA256", sha256(data).hexdigest())
    assert rehearsal.supplied_wheel(wheel) == data


def test_distribution_name_is_closed(tmp_path: Path) -> None:
    wheel = tmp_path / "another-package.whl"
    wheel.write_bytes(b"bytes")
    with pytest.raises(rehearsal.RehearsalRejected, match="^wheel_name$"):
        rehearsal.supplied_wheel(wheel)


@pytest.mark.parametrize("kind", ("directory", "empty", "oversized"))
def test_file_boundary_rejects_unsupported_inputs(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "input"
    if kind == "directory":
        path.mkdir()
    else:
        path.write_bytes(b"" if kind == "empty" else b"12345")
    with pytest.raises(rehearsal.RehearsalRejected, match="^file_boundary$"):
        rehearsal.read_regular(path, 4)


@pytest.mark.skipif(os.name == "nt", reason="Linux operator filesystem boundary")
def test_final_symlink_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "original"
    target.write_bytes(b"bytes")
    link = tmp_path / rehearsal.WHEEL_NAME
    link.symlink_to(target)
    with pytest.raises(rehearsal.RehearsalRejected, match="^file_boundary$"):
        rehearsal.supplied_wheel(link)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX fifo boundary")
def test_fifo_rejects_without_waiting_for_a_writer(tmp_path: Path) -> None:
    fifo = tmp_path / rehearsal.WHEEL_NAME
    os.mkfifo(fifo)
    with pytest.raises(rehearsal.RehearsalRejected, match="^file_boundary$"):
        rehearsal.supplied_wheel(fifo)


def test_existing_output_is_preserved(tmp_path: Path) -> None:
    output = tmp_path / "result"
    output.mkdir()
    preserved = output / "existing.txt"
    preserved.write_bytes(b"retain")
    with pytest.raises(rehearsal.RehearsalRejected, match="^output_boundary$"):
        rehearsal.output_directory(tmp_path / "repo", output)
    assert preserved.read_bytes() == b"retain"
    assert list(output.iterdir()) == [preserved]


def test_output_inside_checkout_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(rehearsal.RehearsalRejected, match="^output_boundary$"):
        rehearsal.output_directory(tmp_path, tmp_path / "result")
    assert not (tmp_path / "result").exists()


@pytest.mark.skipif(os.name == "nt", reason="Linux operator filesystem boundary")
def test_parent_symlink_cannot_redirect_output(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    redirected = tmp_path / "redirect"
    redirected.symlink_to(repo, target_is_directory=True)
    with pytest.raises(rehearsal.RehearsalRejected, match="^output_boundary$"):
        rehearsal.output_directory(repo, redirected / "result")
    assert not (repo / "result").exists()


def test_output_is_created_in_fresh_external_directory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    result = rehearsal.output_directory(repo, tmp_path / "result")
    assert result == tmp_path / "result" and list(result.iterdir()) == []
