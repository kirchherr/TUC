from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tomllib
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest

import tuc.portable_compute_reproduction as reproduction
from tuc.portable_compute_reproduction import (
    PORTABLE_COMPUTE_REPRODUCTION_CLI_NAME,
    PORTABLE_COMPUTE_REPRODUCTION_KIT_SCHEMA_VERSION,
    PORTABLE_COMPUTE_REPRODUCTION_RECEIPT_SCHEMA_VERSION,
    PortableComputeReproductionError,
    assert_portable_compute_reproduction_receipt,
    build_portable_compute_reproduction_kit,
    dump_portable_compute_reproduction_receipt,
    main,
    reproduce_portable_compute,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONSUMER_ROOT = Path("integration/objective_delta")
GOLDEN_ROOT = Path("tests/golden/portable_compute_reproduction")
MANIFEST_GOLDEN = GOLDEN_ROOT / "manifest.json"
RECEIPT_GOLDEN = GOLDEN_ROOT / "receipt.json"
MANIFEST_SCHEMA = Path("schemas/portable_compute_reproduction_kit_manifest.v0.schema.json")
RECEIPT_SCHEMA = Path("schemas/portable_compute_reproduction_receipt.v0.schema.json")
EXPECTED_KIT_DIGEST = (
    "sha256:ddbe9d7e347ef03aa047a27df0272b8991380f20426c1e8be38205421c8ab42e"
)


def test_reproduction_kit_is_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    first_digest = build_portable_compute_reproduction_kit(CONSUMER_ROOT, first)
    second_digest = build_portable_compute_reproduction_kit(CONSUMER_ROOT, second)

    assert first.read_bytes() == second.read_bytes()
    assert first_digest == second_digest == EXPECTED_KIT_DIGEST


def test_reproduction_kit_manifest_matches_golden(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)

    with zipfile.ZipFile(kit) as archive:
        manifest = archive.read(reproduction.REPRODUCTION_MANIFEST_PATH)

    assert manifest == MANIFEST_GOLDEN.read_bytes()


def test_reproduction_receipt_matches_golden(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)

    assert dump_portable_compute_reproduction_receipt(kit) == RECEIPT_GOLDEN.read_text(
        encoding="utf-8"
    )
    report = reproduce_portable_compute(kit)
    assert report["reproduction_status"] == "PASS"
    assert report["reports_byte_identical"] is True
    assert report["independent_reproduction_claim"] is False
    assert report["external_package_code_executed"] is False


def test_reproduction_schemas_are_closed_and_match_goldens() -> None:
    manifest_schema = _load_json(MANIFEST_SCHEMA)
    receipt_schema = _load_json(RECEIPT_SCHEMA)
    manifest = _load_json(MANIFEST_GOLDEN)
    receipt = _load_json(RECEIPT_GOLDEN)

    assert manifest_schema["additionalProperties"] is False
    assert receipt_schema["additionalProperties"] is False
    assert set(cast(list[str], manifest_schema["required"])) == set(manifest)
    assert set(cast(list[str], receipt_schema["required"])) == set(receipt)
    assert manifest_schema["properties"]["schema_version"]["const"] == (
        PORTABLE_COMPUTE_REPRODUCTION_KIT_SCHEMA_VERSION
    )
    assert receipt_schema["properties"]["schema_version"]["const"] == (
        PORTABLE_COMPUTE_REPRODUCTION_RECEIPT_SCHEMA_VERSION
    )


def test_reproduction_archive_has_exact_non_executable_members(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)

    with zipfile.ZipFile(kit) as archive:
        assert tuple(info.filename for info in archive.infolist()) == (
            reproduction.REPRODUCTION_MEMBER_PATHS
        )
        for info in archive.infolist():
            mode = info.external_attr >> 16
            assert info.compress_type == zipfile.ZIP_STORED
            assert stat.S_IFMT(mode) == stat.S_IFREG
            assert stat.S_IMODE(mode) == 0o644
            assert mode & 0o111 == 0
            assert info.date_time == reproduction.REPRODUCTION_ZIP_TIMESTAMP
            assert info.extra == b""
            assert info.comment == b""


def test_reproduction_cli_emits_golden(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    kit = _build_kit(tmp_path)

    assert main([str(kit)]) == 0
    captured = capfd.readouterr()
    assert captured.out == RECEIPT_GOLDEN.read_text(encoding="utf-8")
    assert captured.err == ""


def test_reproduction_cli_rejects_without_path_or_payload_disclosure(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    private = tmp_path / "private-secret-kit.zip"
    private.write_bytes(b"DO_NOT_LOG_THIS")

    assert main([str(private)]) == 2
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == "tuc-reproduce-portable-compute: kit rejected\n"
    assert str(private) not in captured.err
    assert "DO_NOT_LOG_THIS" not in captured.err


@pytest.mark.parametrize("arguments", ([], ["a.zip", "b.zip"]))
def test_reproduction_cli_rejects_ambiguous_arity(
    arguments: list[str],
    capfd: pytest.CaptureFixture[str],
) -> None:
    assert main(arguments) == 2
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == "usage: tuc-reproduce-portable-compute KIT.zip\n"


def test_reproduction_module_entrypoint_matches_golden(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)

    completed = subprocess.run(
        [sys.executable, "-m", "tuc.portable_compute_reproduction", str(kit)],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.stdout == RECEIPT_GOLDEN.read_text(encoding="utf-8")
    assert completed.stderr == ""


def test_reproduction_receipt_rejects_claim_drift(tmp_path: Path) -> None:
    report = reproduce_portable_compute(_build_kit(tmp_path))
    drifted = deepcopy(report)
    drifted["independent_reproduction_claim"] = True

    with pytest.raises(PortableComputeReproductionError, match="independent"):
        assert_portable_compute_reproduction_receipt(drifted)


def test_reproduction_rejects_payload_digest_drift(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)
    members = _read_members(kit)
    members["source_intent.v0.json"] += b"\n"
    drifted = tmp_path / "payload-drift.zip"
    _write_kit(drifted, members)

    with pytest.raises(PortableComputeReproductionError, match="file binding"):
        reproduce_portable_compute(drifted)


def test_reproduction_rejects_byte_different_expected_report(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)
    members = _read_members(kit)
    members["expected_report.json"] += b"\n"
    _refresh_manifest_file_binding(members, "expected_report.json")
    drifted = tmp_path / "report-drift.zip"
    _write_kit(drifted, members)

    with pytest.raises(PortableComputeReproductionError, match="report drift"):
        reproduce_portable_compute(drifted)


def test_reproduction_rejects_compressed_member(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)
    members = _read_members(kit)
    drifted = tmp_path / "compressed.zip"
    _write_kit(
        drifted,
        members,
        compression_overrides={"source_intent.v0.json": zipfile.ZIP_DEFLATED},
    )

    with pytest.raises(PortableComputeReproductionError, match="compression"):
        reproduce_portable_compute(drifted)


def test_reproduction_rejects_executable_member(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)
    members = _read_members(kit)
    drifted = tmp_path / "executable.zip"
    _write_kit(drifted, members, mode_overrides={"manifest.json": 0o755})

    with pytest.raises(PortableComputeReproductionError, match="executable"):
        reproduce_portable_compute(drifted)


def test_reproduction_rejects_duplicate_member(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)
    members = _read_members(kit)
    drifted = tmp_path / "duplicate.zip"
    with pytest.warns(UserWarning, match="Duplicate name"):
        _write_kit(drifted, members, duplicate="manifest.json")

    with pytest.raises(PortableComputeReproductionError, match="member count"):
        reproduce_portable_compute(drifted)


def test_reproduction_rejects_member_order_drift(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)
    members = _read_members(kit)
    drifted = tmp_path / "order.zip"
    _write_kit(drifted, members, member_order=tuple(reversed(members)))

    with pytest.raises(PortableComputeReproductionError, match="member order"):
        reproduce_portable_compute(drifted)


def test_reproduction_rejects_duplicate_manifest_key(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)
    members = _read_members(kit)
    manifest = members["manifest.json"].decode("utf-8")
    members["manifest.json"] = manifest.replace(
        '{\n  "archive_policy":',
        '{\n  "schema_version": "duplicate",\n  "archive_policy":',
    ).encode("utf-8")
    drifted = tmp_path / "duplicate-key.zip"
    _write_kit(drifted, members)

    with pytest.raises(PortableComputeReproductionError, match="duplicate key"):
        reproduce_portable_compute(drifted)


def test_reproduction_rejects_oversized_archive_before_zip_parse(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.zip"
    oversized.write_bytes(b"x" * (reproduction.MAX_REPRODUCTION_ARCHIVE_BYTES + 1))

    with pytest.raises(PortableComputeReproductionError, match="byte limit"):
        reproduce_portable_compute(oversized)


def test_reproduction_builder_refuses_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "existing.zip"
    output.write_bytes(b"keep")

    with pytest.raises(PortableComputeReproductionError, match="must not exist"):
        build_portable_compute_reproduction_kit(CONSUMER_ROOT, output)
    assert output.read_bytes() == b"keep"


def test_reproduction_builder_rejects_semantic_source_drift(tmp_path: Path) -> None:
    consumer = tmp_path / "consumer"
    shutil.copytree(CONSUMER_ROOT, consumer)
    source_path = consumer / "source_intent.v0.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["name"] = "drifted_reproduction"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    output = tmp_path / "must-not-exist.zip"

    with pytest.raises(PortableComputeReproductionError, match="source evidence"):
        build_portable_compute_reproduction_kit(consumer, output)
    assert not output.exists()


@pytest.mark.skipif(os.name == "nt", reason="Windows symlink creation needs privileges")
def test_reproduction_rejects_symlink_kit(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)
    link = tmp_path / "linked.zip"
    link.symlink_to(kit)

    with pytest.raises(PortableComputeReproductionError, match="symlink"):
        reproduce_portable_compute(link)


def test_wheel_registers_reproduction_console_script() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["scripts"][PORTABLE_COMPUTE_REPRODUCTION_CLI_NAME] == (
        "tuc.portable_compute_reproduction:main"
    )


@pytest.mark.parametrize(
    ("path", "marker"),
    (
        (
            Path("docs/OBJECTIVE_DELTA_REPRODUCTION_KIT.md"),
            "# Objective Delta Reproduction Kit",
        ),
        (
            Path("rfcs/0293-objective-delta-reproduction-kit.md"),
            "# RFC 0293: Objective Delta Reproduction Kit",
        ),
        (Path("README.md"), "Objective Delta Reproduction Kit"),
        (Path("ROADMAP.md"), "Publish the Objective Delta Reproduction Kit"),
        (Path("TUC_MASTER_PLAN.md"), "Objective Delta Reproduction Kit"),
        (Path("docs/ROADMAP_STATUS.md"), "Objective Delta Reproduction Kit"),
        (Path("docs/RELEASE_SECURITY.md"), "Objective Delta data-only reproduction"),
        (Path("docs/RELEASE_GOVERNANCE.md"), "Objective Delta reproduction kit"),
        (
            Path("docs/DEVELOPMENT_ENVIRONMENT.md"),
            "build_portable_compute_reproduction_kit.py",
        ),
    ),
)
def test_reproduction_contract_is_bound_into_project_guidance(
    path: Path,
    marker: str,
) -> None:
    assert marker in path.read_text(encoding="utf-8")


def test_built_wheel_runs_external_reproduction(tmp_path: Path) -> None:
    kit = _build_kit(tmp_path)
    wheel_directory = tmp_path / "wheel"
    wheel_directory.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(wheel_directory),
        ],
        check=True,
        cwd=PROJECT_ROOT,
        capture_output=True,
        timeout=120,
    )
    wheels = tuple(wheel_directory.glob("*.whl"))
    assert len(wheels) == 1

    subprocess.run(
        [
            sys.executable,
            str(
                PROJECT_ROOT
                / "scripts"
                / "verify_external_portable_compute_reproduction.py"
            ),
            "--wheel",
            str(wheels[0]),
            "--kit",
            str(kit),
            "--expected-receipt",
            str(PROJECT_ROOT / RECEIPT_GOLDEN),
            "--source-root",
            str(PROJECT_ROOT),
        ],
        check=True,
        cwd=tmp_path,
        capture_output=True,
        timeout=240,
    )


def _build_kit(tmp_path: Path) -> Path:
    kit = tmp_path / "objective-delta-reproduction.zip"
    assert build_portable_compute_reproduction_kit(CONSUMER_ROOT, kit) == (
        EXPECTED_KIT_DIGEST
    )
    return kit


def _read_members(kit: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(kit) as archive:
        return {info.filename: archive.read(info) for info in archive.infolist()}


def _write_kit(
    path: Path,
    members: dict[str, bytes],
    *,
    member_order: tuple[str, ...] | None = None,
    compression_overrides: dict[str, int] | None = None,
    mode_overrides: dict[str, int] | None = None,
    duplicate: str | None = None,
) -> None:
    order = member_order or tuple(members)
    compression = compression_overrides or {}
    modes = mode_overrides or {}
    with zipfile.ZipFile(path, "x", allowZip64=False) as archive:
        for name in order:
            info = reproduction._canonical_zip_info(name)
            info.compress_type = compression.get(name, zipfile.ZIP_STORED)
            info.external_attr = (stat.S_IFREG | modes.get(name, 0o644)) << 16
            archive.writestr(info, members[name])
        if duplicate is not None:
            archive.writestr(reproduction._canonical_zip_info(duplicate), members[duplicate])


def _refresh_manifest_file_binding(members: dict[str, bytes], path: str) -> None:
    manifest = json.loads(members["manifest.json"])
    for item in manifest["files"]:
        if item["path"] == path:
            item["size_bytes"] = len(members[path])
            item["sha256"] = reproduction._digest_bytes(members[path])
            break
    members["manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if type(payload) is not dict:
        raise TypeError("expected JSON object")
    return cast(dict[str, Any], payload)
