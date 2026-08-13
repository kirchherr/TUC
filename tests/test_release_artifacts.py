from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
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


def test_write_attestation_verification_receipt_is_bounded_and_digest_bound(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / "dist"
    artifact_dir.mkdir()
    artifact = artifact_dir / "tuc-source-ingestion-worker.oci.tar"
    artifact.write_bytes(b"verified OCI archive")
    output = artifact_dir / "tuc-source-ingestion-worker.attestation-verification.json"
    result_path = tmp_path / "verification.json"
    result_path.write_text(
        json.dumps(_attestation_verification_result(artifact)),
        encoding="utf-8",
    )
    writer = _load_module("write_github_attestation_verification_receipt.py")

    report = writer.write_receipt(
        artifact,
        output,
        verification_result_path=result_path,
        **_attestation_context(),
    )

    expected_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert report["artifact_digest"] == f"sha256:{expected_digest}"
    assert report["artifact_size_bytes"] == artifact.stat().st_size
    assert report["attestation_verified"] is True
    assert report["verified_attestation_count"] == 1
    assert report["release_tag_trigger"] is False
    assert report["protected_tag_policy_verified"] is False
    assert report["external_consumer_verification"] is False
    assert report["public_registry_image"] is False
    assert report["production_source_ingestion"] is False
    assert report["execution_permission"] is False
    assert output.stat().st_size <= writer.MAX_RECEIPT_BYTES
    assert json.loads(output.read_text(encoding="utf-8")) == report
    unsigned = dict(report)
    report_digest = unsigned.pop("report_digest")
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert report_digest == f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def test_attestation_verification_receipt_marks_only_push_v_tag_as_release_trigger(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "tuc-source-ingestion-worker.oci.tar"
    artifact.write_bytes(b"verified OCI archive")
    writer = _load_module("write_github_attestation_verification_receipt.py")
    context = _attestation_context()
    context.update(event_name="push", source_ref="refs/tags/v0.1.0")

    report = writer.build_receipt(
        artifact,
        verification_result=_attestation_verification_result(artifact),
        **context,
    )

    assert report["release_tag_trigger"] is True
    assert report["protected_tag_policy_verified"] is False
    assert report["external_consumer_verification"] is False
    assert report["public_registry_image"] is False


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("repository", "kirchherr/TUC\nleak", "repository"),
        ("source_commit", "0" * 39, "source commit"),
        ("source_ref", "refs/heads/../main", "source ref"),
        ("event_name", "pull_request", "event"),
        ("run_id", 0, "run id"),
        ("run_attempt", 101, "run attempt"),
        ("runner_environment", "self-hosted", "runner environment"),
        ("gh_version", "gh version 2.83.0\nsecret", "GitHub CLI version"),
    ],
)
def test_attestation_verification_receipt_rejects_untrusted_context(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    artifact = tmp_path / "tuc-source-ingestion-worker.oci.tar"
    artifact.write_bytes(b"verified OCI archive")
    writer = _load_module("write_github_attestation_verification_receipt.py")
    context = _attestation_context()
    context[field] = value

    with pytest.raises(ValueError, match=message):
        writer.build_receipt(
            artifact,
            verification_result=_attestation_verification_result(artifact),
            **context,
        )


def test_attestation_verification_receipt_rejects_output_escape(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "dist"
    artifact_dir.mkdir()
    artifact = artifact_dir / "tuc-source-ingestion-worker.oci.tar"
    artifact.write_bytes(b"verified OCI archive")
    writer = _load_module("write_github_attestation_verification_receipt.py")
    result_path = tmp_path / "verification.json"
    result_path.write_text(
        json.dumps(_attestation_verification_result(artifact)),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="output path"):
        writer.write_receipt(
            artifact,
            tmp_path / "tuc-source-ingestion-worker.attestation-verification.json",
            verification_result_path=result_path,
            **_attestation_context(),
        )


@pytest.mark.parametrize("result", [[], {}, [{"verificationResult": {}}]])
def test_attestation_verification_receipt_rejects_malformed_verifier_result(
    tmp_path: Path,
    result: object,
) -> None:
    artifact = tmp_path / "tuc-source-ingestion-worker.oci.tar"
    artifact.write_bytes(b"verified OCI archive")
    writer = _load_module("write_github_attestation_verification_receipt.py")

    with pytest.raises(ValueError, match="result"):
        writer.build_receipt(
            artifact,
            verification_result=result,
            **_attestation_context(),
        )


def test_attestation_verification_receipt_rejects_verifier_digest_drift(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "tuc-source-ingestion-worker.oci.tar"
    artifact.write_bytes(b"verified OCI archive")
    writer = _load_module("write_github_attestation_verification_receipt.py")
    result = _attestation_verification_result(artifact)
    result[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"] = (
        "0" * 64
    )

    with pytest.raises(ValueError, match="subject digest"):
        writer.build_receipt(
            artifact,
            verification_result=result,
            **_attestation_context(),
        )


def test_attestation_verification_receipt_schema_matches_report(tmp_path: Path) -> None:
    artifact = tmp_path / "tuc-source-ingestion-worker.oci.tar"
    artifact.write_bytes(b"verified OCI archive")
    writer = _load_module("write_github_attestation_verification_receipt.py")
    schema = json.loads(
        Path("schemas/github_attestation_verification_receipt.v0.schema.json").read_text(
            encoding="utf-8"
        )
    )

    report = writer.build_receipt(
        artifact,
        verification_result=_attestation_verification_result(artifact),
        **_attestation_context(),
    )

    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == writer.SCHEMA_VERSION
    assert set(schema["required"]) == set(report)
    assert set(schema["properties"]) == set(report)


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


def test_ci_toolchain_is_version_and_hash_locked() -> None:
    lines = [
        line
        for line in Path("requirements/ci.txt").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    requirement_pattern = re.compile(
        r"([a-z0-9-]+)==([0-9]+(?:\.[0-9]+){1,3}) "
        r"--hash=sha256:([a-f0-9]{64})"
    )

    assert lines[0] == "--only-binary=:all:"
    requirements = [requirement_pattern.fullmatch(line) for line in lines[1:]]
    assert all(requirements)
    package_names = [match.group(1) for match in requirements if match is not None]
    assert package_names == sorted(package_names)
    assert len(package_names) == len(set(package_names)) == 21
    assert set(package_names) == {
        "ast-serialize",
        "build",
        "execnet",
        "hypothesis",
        "iniconfig",
        "librt",
        "mypy",
        "mypy-extensions",
        "numpy",
        "packaging",
        "pathspec",
        "pluggy",
        "pygments",
        "pyproject-hooks",
        "pytest",
        "pytest-xdist",
        "ruff",
        "setuptools",
        "sortedcontainers",
        "typing-extensions",
        "wheel",
    }


def test_ci_and_release_use_locked_toolchain_without_build_isolation() -> None:
    install_lock = "python -m pip install --require-hashes -r requirements/ci.txt"
    install_project = "python -m pip install --no-deps --no-build-isolation -e ."

    for workflow_path in (
        Path(".github/workflows/ci.yml"),
        Path(".github/workflows/release-artifacts.yml"),
    ):
        workflow = workflow_path.read_text(encoding="utf-8")
        assert workflow.count(install_lock) == 1
        assert workflow.count(install_project) == 1
        assert 'pip install -e ".[dev]"' not in workflow
        assert workflow.count("run: pytest -q -n 4") == 1


def test_ci_and_release_declare_repository_example_import_path() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    for workflow_path in (
        Path(".github/workflows/ci.yml"),
        Path(".github/workflows/release-artifacts.yml"),
    ):
        workflow = workflow_path.read_text(encoding="utf-8")
        assert workflow.count("PYTHONPATH: ${{ github.workspace }}") == 1
    assert 'pythonpath = [".", "src"]' in pyproject


@pytest.mark.skipif(os.name == "nt", reason="Windows symlink creation needs privileges")
def test_external_consumer_verifier_rejects_symlink_inputs(tmp_path: Path) -> None:
    verifier = _load_module("verify_external_backend_consumer.py")
    wheel = tmp_path / "tuc.whl"
    wheel.write_bytes(b"not executed")
    wheel_link = tmp_path / "wheel-link.whl"
    wheel_link.symlink_to(wheel)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    source = tmp_path / "source"
    source.mkdir()

    with pytest.raises(ValueError, match="wheel must not be a symlink"):
        verifier.verify_external_consumer(
            wheel_path=wheel_link,
            consumer_source=consumer,
            source_root=source,
        )


@pytest.mark.skipif(os.name == "nt", reason="Windows symlink creation needs privileges")
def test_external_consumer_verifier_rejects_nested_symlink(tmp_path: Path) -> None:
    verifier = _load_module("verify_external_backend_consumer.py")
    wheel = tmp_path / "tuc.whl"
    wheel.write_bytes(b"not executed")
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    for filename in (
        "backend_package.v0.json",
        "consumer.py",
        "expected_report.json",
    ):
        (consumer / filename).write_text("{}\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("not copied", encoding="utf-8")
    (consumer / "escape.txt").symlink_to(outside)
    source = tmp_path / "source"
    source.mkdir()

    with pytest.raises(ValueError, match="must not contain symlinks"):
        verifier.verify_external_consumer(
            wheel_path=wheel,
            consumer_source=consumer,
            source_root=source,
        )


def test_external_consumer_verifier_rejects_consumer_source_drift(
    tmp_path: Path,
) -> None:
    verifier = _load_module("verify_external_backend_consumer.py")
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    for filename in verifier.OBJECTIVE_GAMMA_CONSUMER_FILES:
        (consumer / filename).write_text("changed\n", encoding="utf-8")

    with pytest.raises(ValueError, match="consumer source digest mismatch"):
        verifier._validate_consumer_tree(consumer)


def test_external_consumer_verifier_rejects_unexpected_consumer_file(
    tmp_path: Path,
) -> None:
    verifier = _load_module("verify_external_backend_consumer.py")
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    source_consumer = Path("integration/objective_gamma")
    for filename in verifier.OBJECTIVE_GAMMA_CONSUMER_FILES:
        (consumer / filename).write_bytes((source_consumer / filename).read_bytes())
    (consumer / "unexpected.py").write_text("raise SystemExit(1)\n", encoding="utf-8")

    with pytest.raises(ValueError, match="file set changed"):
        verifier._validate_consumer_tree(consumer)


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
    assert workflow.count("gh attestation verify") == 1
    assert '--repo "$GITHUB_REPOSITORY"' in workflow
    assert "--signer-repo" not in workflow
    assert (
        '--signer-workflow "$GITHUB_REPOSITORY/.github/workflows/release-artifacts.yml"'
        in workflow
    )
    assert workflow.count("--signer-workflow") == 1
    assert '--source-digest "$GITHUB_SHA"' in workflow
    assert '--source-ref "$GITHUB_REF"' in workflow
    assert '--cert-oidc-issuer "https://token.actions.githubusercontent.com"' in workflow
    assert '--predicate-type "https://slsa.dev/provenance/v1"' in workflow
    assert "--deny-self-hosted-runners" in workflow
    assert "--limit 8" in workflow
    assert (
        '--format json >"$RUNNER_TEMP/tuc-worker-attestation-verification.json"'
        in workflow
    )
    assert "scripts/write_github_attestation_verification_receipt.py" in workflow
    assert (
        '--verification-result "$RUNNER_TEMP/tuc-worker-attestation-verification.json"'
        in workflow
    )
    assert "dist/*.attestation-verification.json" in workflow
    assert "dist/*.oci-verification.json" in workflow
    assert "dist/*.oci.tar" in workflow
    assert workflow.index("gh attestation verify") < workflow.index(
        "scripts/write_artifact_checksums.py"
    )
    assert 'echo "$GH_TOKEN"' not in workflow


def _attestation_context() -> dict[str, object]:
    return {
        "repository": "kirchherr/TUC",
        "source_commit": "8c9cc155d6d19c827cac8472892681c58a91a335",
        "source_ref": "refs/heads/codex/neutral-runtime-defaults",
        "event_name": "workflow_dispatch",
        "run_id": 123456789,
        "run_attempt": 1,
        "runner_environment": "github-hosted",
        "gh_version": "gh version 2.83.0 (2026-08-01)",
    }


def _attestation_verification_result(artifact: Path) -> list[dict[str, object]]:
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    return [
        {
            "attestation": {"bundle": "verified-but-omitted-from-receipt"},
            "verificationResult": {
                "statement": {
                    "predicateType": "https://slsa.dev/provenance/v1",
                    "subject": [
                        {
                            "name": artifact.name,
                            "digest": {"sha256": digest},
                        }
                    ],
                }
            },
        }
    ]


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
