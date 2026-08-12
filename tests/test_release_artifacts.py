from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import re
import tarfile
from pathlib import Path

import pytest


def _load_module(script_name: str):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name.removesuffix(".py"), script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_sbom_uses_cyclonedx_contract(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "sample"
version = "1.2.3"
dependencies = ["numpy>=1.26"]

[project.urls]
Repository = "https://example.test/sample"
""".strip(),
        encoding="utf-8",
    )
    generate_sbom = _load_module("generate_sbom.py")

    sbom = generate_sbom.generate_sbom(tmp_path)

    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.6"
    assert sbom["metadata"]["component"]["name"] == "sample"
    assert sbom["metadata"]["component"]["version"] == "1.2.3"
    assert sbom["components"][0]["name"] == "numpy"
    assert sbom["dependencies"][0]["ref"] == "pkg:pypi/sample@1.2.3"
    assert sbom["dependencies"][0]["dependsOn"]
    json.dumps(sbom)


def test_write_artifact_checksums_excludes_output_file(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "dist"
    artifact_dir.mkdir()
    wheel = artifact_dir / "sample-1.2.3-py3-none-any.whl"
    sdist = artifact_dir / "sample-1.2.3.tar.gz"
    output = artifact_dir / "SHA256SUMS"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    output.write_text("old\n", encoding="utf-8")
    write_checksums = _load_module("write_artifact_checksums.py")

    lines = write_checksums.write_checksums(artifact_dir, output)

    expected_sdist = hashlib.sha256(b"sdist").hexdigest()
    expected_wheel = hashlib.sha256(b"wheel").hexdigest()
    assert lines == [
        f"{expected_wheel}  sample-1.2.3-py3-none-any.whl",
        f"{expected_sdist}  sample-1.2.3.tar.gz",
    ]
    assert "SHA256SUMS" not in output.read_text(encoding="utf-8")


def test_release_workflow_actions_are_sha_pinned() -> None:
    workflow_path = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release-artifacts.yml"
    )
    workflow_text = workflow_path.read_text(encoding="utf-8")
    action_refs = re.findall(
        r"uses:\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([0-9a-f]{40})"
        r"(?:\s+#\s+v[0-9.]+)?",
        workflow_text,
    )
    unpinned_action_refs = re.findall(
        r"uses:\s+[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@([A-Za-z_/.-]*v[0-9][A-Za-z0-9_.-]*)",
        workflow_text,
    )

    assert not unpinned_action_refs
    assert action_refs == [
        ("actions/checkout", "de0fac2e4500dabe0009e67214ff5f5447ce83dd"),
        ("actions/setup-python", "a309ff8b426b58ec0e2a45f0f869d46889d02405"),
        ("docker/setup-buildx-action", "bb05f3f5519dd87d3ba754cc423b652a5edd6d2c"),
        ("actions/attest", "59d89421af93a897026c735860bf21b6eb4f7b26"),
        ("actions/attest", "59d89421af93a897026c735860bf21b6eb4f7b26"),
        ("actions/attest", "59d89421af93a897026c735860bf21b6eb4f7b26"),
        ("actions/attest", "59d89421af93a897026c735860bf21b6eb4f7b26"),
        ("actions/upload-artifact", "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"),
        ("actions/download-artifact", "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"),
        ("pypa/gh-action-pypi-publish", "cef221092ed1bacb1cc03d23a2d87d1d172e277b"),
    ]


def test_source_worker_sbom_is_deterministic_and_material_bound() -> None:
    project_root = Path(__file__).resolve().parents[1]
    module = _load_module("generate_source_worker_sbom.py")

    first = module.generate_source_worker_sbom(project_root)
    second = module.generate_source_worker_sbom(project_root)

    assert first == second
    assert first["bomFormat"] == "CycloneDX"
    assert first["specVersion"] == "1.6"
    component = first["metadata"]["component"]
    assert component["type"] == "container"
    assert component["name"] == "tuc-source-ingestion-worker"
    assert component["version"] == "research-v0"
    properties = {item["name"]: item["value"] for item in component["properties"]}
    assert properties["tuc:platform"] == "linux/amd64"
    assert set(properties) == {
        "tuc:material:dockerfile:sha256",
        "tuc:material:requirements:sha256",
        "tuc:material:worker_source:sha256",
        "tuc:platform",
    }
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", value)
        for name, value in properties.items()
        if name.endswith(":sha256")
    )
    components = {item["name"]: item for item in first["components"]}
    assert components["python"]["hashes"][0]["content"] == (
        "4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2"
    )
    assert components["numpy"]["version"] == "2.4.4"
    assert components["numpy"]["hashes"][0]["content"] == (
        "81f4a14bee47aec54f883e0cad2d73986640c1590eb9bfaaba7ad17394481e6e"
    )


def test_source_worker_oci_archive_verifier_accepts_fixed_config(tmp_path: Path) -> None:
    verifier = _load_module("verify_source_worker_oci_archive.py")
    archive_path = tmp_path / "worker.oci.tar"
    _write_worker_oci_archive(archive_path)

    report = verifier.verify_source_worker_oci_archive(archive_path)

    assert report["status"] == "PASS"
    assert report["platform"] == "linux/amd64"
    assert report["user"] == "10001:10001"
    assert report["working_dir"] == "/run/tuc"
    assert report["layer_count"] == 1
    assert report["rootfs_diff_id_count"] == 1
    assert re.fullmatch(r"sha256:[a-f0-9]{64}", str(report["archive_digest"]))


@pytest.mark.parametrize(
    ("config_override", "message"),
    [
        ({"User": "0:0"}, "user"),
        ({"WorkingDir": "/workspace"}, "working directory"),
        ({"Entrypoint": ["sh", "-c", "id"]}, "entrypoint"),
        ({"Cmd": ["sh"]}, "command override"),
    ],
)
def test_source_worker_oci_archive_verifier_rejects_runtime_drift(
    tmp_path: Path,
    config_override: dict[str, object],
    message: str,
) -> None:
    verifier = _load_module("verify_source_worker_oci_archive.py")
    archive_path = tmp_path / "worker.oci.tar"
    _write_worker_oci_archive(archive_path, config_override=config_override)

    with pytest.raises(ValueError, match=message):
        verifier.verify_source_worker_oci_archive(archive_path)


def test_source_worker_oci_archive_verifier_rejects_digest_tamper(tmp_path: Path) -> None:
    verifier = _load_module("verify_source_worker_oci_archive.py")
    archive_path = tmp_path / "worker.oci.tar"
    _write_worker_oci_archive(archive_path, tamper_layer=True)

    with pytest.raises(ValueError, match="digest"):
        verifier.verify_source_worker_oci_archive(archive_path)


def test_source_worker_oci_archive_verifier_rejects_path_traversal(tmp_path: Path) -> None:
    verifier = _load_module("verify_source_worker_oci_archive.py")
    archive_path = tmp_path / "worker.oci.tar"
    _write_worker_oci_archive(archive_path, extra_member="../escape")

    with pytest.raises(ValueError, match="path"):
        verifier.verify_source_worker_oci_archive(archive_path)


def test_source_worker_oci_archive_verifier_rejects_unreferenced_member(
    tmp_path: Path,
) -> None:
    verifier = _load_module("verify_source_worker_oci_archive.py")
    archive_path = tmp_path / "worker.oci.tar"
    _write_worker_oci_archive(archive_path, extra_member="unreferenced")

    with pytest.raises(ValueError, match="unreferenced member"):
        verifier.verify_source_worker_oci_archive(archive_path)


def test_source_worker_oci_archive_verifier_rejects_rootfs_cardinality_drift(
    tmp_path: Path,
) -> None:
    verifier = _load_module("verify_source_worker_oci_archive.py")
    archive_path = tmp_path / "worker.oci.tar"
    _write_worker_oci_archive(archive_path, extra_diff_id=True)

    with pytest.raises(ValueError, match="cardinality"):
        verifier.verify_source_worker_oci_archive(archive_path)


def test_release_workflow_attests_worker_archive_and_sbom() -> None:
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/release-artifacts.yml"
    ).read_text(encoding="utf-8")

    assert "--platform linux/amd64" in workflow
    assert "version: v0.34.1" in workflow
    assert (
        "image=moby/buildkit:v0.30.0@sha256:"
        "0168606be2315b7c807a03b3d8aa79beefdb31c98740cebdffdfeebf31190c9f"
    ) in workflow
    assert "buildkitd-flags: --cdi-disabled" in workflow
    assert "--allow-insecure-entitlement" not in workflow
    assert "--provenance=false" in workflow
    assert "--sbom=false" in workflow
    assert "type=oci,dest=dist/tuc-source-ingestion-worker.oci.tar" in workflow
    assert "scripts/verify_source_worker_oci_archive.py" in workflow
    assert "scripts/generate_source_worker_sbom.py" in workflow
    assert workflow.count("subject-path: dist/tuc-source-ingestion-worker.oci.tar") == 2
    assert "sbom-path: dist/tuc-source-ingestion-worker.cdx.json" in workflow
    assert "dist/*.oci-verification.json" in workflow
    assert "dist/*.oci.tar" in workflow


def _write_worker_oci_archive(
    path: Path,
    *,
    config_override: dict[str, object] | None = None,
    tamper_layer: bool = False,
    extra_member: str | None = None,
    extra_diff_id: bool = False,
) -> None:
    layer = b"layer"
    layer_digest = hashlib.sha256(layer).hexdigest()
    runtime_config: dict[str, object] = {
        "User": "10001:10001",
        "WorkingDir": "/run/tuc",
        "Entrypoint": [
            "python",
            "-I",
            "/opt/tuc/src/tuc/frontend/_isolated_source_ingestion_worker.py",
            "--oci",
        ],
    }
    runtime_config.update(config_override or {})
    config = _json_bytes(
        {
            "architecture": "amd64",
            "os": "linux",
            "config": runtime_config,
            "rootfs": {
                "type": "layers",
                "diff_ids": [
                    f"sha256:{layer_digest}",
                    *(["sha256:" + "0" * 64] if extra_diff_id else []),
                ],
            },
        }
    )
    config_digest = hashlib.sha256(config).hexdigest()
    manifest = _json_bytes(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "digest": f"sha256:{config_digest}",
                "size": len(config),
            },
            "layers": [
                {
                    "mediaType": "application/vnd.oci.image.layer.v1.tar",
                    "digest": f"sha256:{layer_digest}",
                    "size": len(layer),
                }
            ],
        }
    )
    manifest_digest = hashlib.sha256(manifest).hexdigest()
    index = _json_bytes(
        {
            "schemaVersion": 2,
            "manifests": [
                {
                    "mediaType": "application/vnd.oci.image.manifest.v1+json",
                    "digest": f"sha256:{manifest_digest}",
                    "size": len(manifest),
                    "platform": {"architecture": "amd64", "os": "linux"},
                }
            ],
        }
    )
    members = {
        "oci-layout": _json_bytes({"imageLayoutVersion": "1.0.0"}),
        "index.json": index,
        f"blobs/sha256/{manifest_digest}": manifest,
        f"blobs/sha256/{config_digest}": config,
        f"blobs/sha256/{layer_digest}": b"lAyer" if tamper_layer else layer,
    }
    if extra_member is not None:
        members[extra_member] = b"escape"
    with tarfile.open(path, mode="w") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
