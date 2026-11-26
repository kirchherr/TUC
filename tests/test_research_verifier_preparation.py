"""Authenticate before archive parsing or output; never execute returned bytes."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tarfile
from hashlib import sha256
from pathlib import Path

import pytest

from scripts import prepare_research_verifier as verifier

ELF = bytearray(64)
ELF[:6] = b"\x7fELF\x02\x01"
ELF[18:20] = b"\x3e\x00"
PAYLOAD = bytes(ELF) + b"unit fixture, not an executable program"


def archive_bytes(entries: list[tuple[str, bytes, bytes]]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, data, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(data) if kind == tarfile.REGTYPE else 0
            info.linkname = "elsewhere" if kind in {tarfile.SYMTYPE, tarfile.LNKTYPE} else ""
            archive.addfile(info, io.BytesIO(data) if info.size else None)
    return stream.getvalue()


def fixture_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data: bytes,
) -> Path:
    path = tmp_path / verifier.ARCHIVE_NAME
    path.write_bytes(data)
    monkeypatch.setattr(verifier, "ARCHIVE_SHA256", sha256(data).hexdigest())
    monkeypatch.setattr(verifier, "ARCHIVE_BYTES", len(data))
    monkeypatch.setattr(verifier, "BINARY_SHA256", sha256(PAYLOAD).hexdigest())
    monkeypatch.setattr(verifier, "BINARY_BYTES", len(PAYLOAD))
    return path


def test_changed_archive_rejects_before_tar_or_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / verifier.ARCHIVE_NAME
    path.write_bytes(b"must not be parsed or run")

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("archive parsing reached before authentication")

    monkeypatch.setattr(verifier.tarfile, "open", forbidden)
    with pytest.raises(verifier.PreparationRejected, match="^archive_digest$"):
        verifier.prepare(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_preparation_copies_only_fixed_bytes_without_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = archive_bytes([(verifier.MEMBER, PAYLOAD, tarfile.REGTYPE),
                          ("package/ignored.txt", b"ignored", tarfile.REGTYPE)])
    path = fixture_archive(tmp_path, monkeypatch, data)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("preparation must never execute the binary")

    monkeypatch.setattr(subprocess, "run", forbidden)
    output = tmp_path / "output"
    result = verifier.prepare(path, output)
    assert {p.name for p in output.iterdir()} == {"gh", "tool.json"}
    assert (output / "gh").read_bytes() == PAYLOAD
    assert result["executable_run_by_preparation"] is False
    assert result["system_installation"] is False
    assert json.loads((output / "tool.json").read_bytes()) == result


@pytest.mark.parametrize("kind", (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE))
def test_target_special_files_reject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: bytes,
) -> None:
    data = archive_bytes([(verifier.MEMBER, b"", kind)])
    path = fixture_archive(tmp_path, monkeypatch, data)
    with pytest.raises(verifier.PreparationRejected, match="^archive_boundary$"):
        verifier.prepare(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("name", ("../outside", "/absolute", "dir\\file", "C:/file"))
def test_traversal_and_platform_redirect_names_reject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str,
) -> None:
    path = fixture_archive(tmp_path, monkeypatch, archive_bytes([
        (name, b"untrusted", tarfile.REGTYPE), (verifier.MEMBER, PAYLOAD, tarfile.REGTYPE),
    ]))
    with pytest.raises(verifier.PreparationRejected, match="^archive_boundary$"):
        verifier.prepare(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_duplicate_target_rejects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    entry = (verifier.MEMBER, PAYLOAD, tarfile.REGTYPE)
    path = fixture_archive(tmp_path, monkeypatch, archive_bytes([entry, entry]))
    with pytest.raises(verifier.PreparationRejected, match="^archive_boundary$"):
        verifier.prepare(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("kind", ("missing", "changed", "wrong_arch", "oversized", "malformed"))
def test_executable_and_archive_boundaries_reject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str,
) -> None:
    binary = PAYLOAD
    if kind == "changed":
        binary = PAYLOAD[:-1] + b"!"
    elif kind == "wrong_arch":
        binary = PAYLOAD[:18] + b"\xb7\x00" + PAYLOAD[20:]
    elif kind == "oversized":
        binary += b"x"
    entries = [("other" if kind == "missing" else verifier.MEMBER, binary, tarfile.REGTYPE)]
    data = b"not tar" if kind == "malformed" else archive_bytes(entries)
    path = fixture_archive(tmp_path, monkeypatch, data)
    if kind == "wrong_arch":
        monkeypatch.setattr(verifier, "BINARY_SHA256", sha256(binary).hexdigest())
    with pytest.raises(verifier.PreparationRejected):
        verifier.prepare(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_existing_output_preserved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = archive_bytes([(verifier.MEMBER, PAYLOAD, tarfile.REGTYPE)])
    path = fixture_archive(tmp_path, monkeypatch, data)
    output = tmp_path / "output"
    output.mkdir()
    (output / "retain").write_bytes(b"keep")
    with pytest.raises(verifier.PreparationRejected, match="^output_boundary$"):
        verifier.prepare(path, output)
    assert (output / "retain").read_bytes() == b"keep"
    assert list(output.iterdir()) == [output / "retain"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink boundary")
@pytest.mark.parametrize("kind", ("archive", "parent"))
def test_input_symlinks_reject(tmp_path: Path, kind: str) -> None:
    target = tmp_path / "target"
    target.mkdir()
    original = target / "archive"
    original.write_bytes(b"bytes")
    link = tmp_path / "link"
    link.symlink_to(target if kind == "parent" else original, target_is_directory=kind == "parent")
    path = link / "archive" if kind == "parent" else link
    with pytest.raises(verifier.PreparationRejected, match="^file_boundary$"):
        verifier.authenticated_archive(path)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO boundary")
def test_input_fifo_rejects_without_opening(tmp_path: Path) -> None:
    path = tmp_path / "pipe"
    os.mkfifo(path)
    with pytest.raises(verifier.PreparationRejected, match="^file_boundary$"):
        verifier.authenticated_archive(path)


@pytest.mark.parametrize("kind", ("directory", "empty", "oversized"))
def test_regular_file_size_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str,
) -> None:
    path = tmp_path / "input"
    monkeypatch.setattr(verifier, "MAX_ARCHIVE", 4)
    if kind == "directory":
        path.mkdir()
    else:
        path.write_bytes(b"" if kind == "empty" else b"12345")
    with pytest.raises(verifier.PreparationRejected, match="^file_boundary$"):
        verifier.authenticated_archive(path)


@pytest.mark.skipif(os.name == "nt", reason="POSIX output redirect boundary")
def test_output_parent_symlink_cannot_redirect_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = archive_bytes([(verifier.MEMBER, PAYLOAD, tarfile.REGTYPE)])
    archive = fixture_archive(tmp_path, monkeypatch, data)
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(verifier.PreparationRejected, match="^output_boundary$"):
        verifier.prepare(archive, link / "output")
    assert list(target.iterdir()) == []


def test_cli_reports_rejection_without_operator_paths(tmp_path: Path) -> None:
    path = tmp_path / "untrusted"
    path.write_bytes(b"changed archive")
    script = Path(__file__).resolve().parents[1] / "scripts/prepare_research_verifier.py"
    process = subprocess.run([sys.executable, "-I", "-S", str(script), "--archive", str(path),
                              "--output", str(tmp_path / "output")],
                             capture_output=True, check=False, timeout=15)
    assert process.returncode == 1
    assert json.loads(process.stdout) == {"status": "REJECTED", "reason": "archive_digest"}
    assert not process.stderr and b"\r" not in process.stdout
