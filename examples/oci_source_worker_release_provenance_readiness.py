"""Emit OCI source-worker release provenance readiness evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

SCHEMA_VERSION = "tuc.oci_source_worker_release_provenance_readiness_report.v0"
READINESS_CONTRACT = "oci_source_worker.release_provenance_readiness.data_only.v0"
READINESS_STATUS = "PASS"
READINESS_CLAIM = (
    "release_workflow_can_emit_attest_and_policy_verify_oci_archive_and_worker_sbom"
)
ARTIFACT_NAME = "tuc-source-ingestion-worker.oci.tar"
ARTIFACT_FORMAT = "oci_image_layout_tar"
PLATFORM = "linux/amd64"
SBOM_FORMAT = "CycloneDX-1.6"
ATTEST_ACTION = "actions/attest@59d89421af93a897026c735860bf21b6eb4f7b26"
BUILDX_ACTION = (
    "docker/setup-buildx-action@bb05f3f5519dd87d3ba754cc423b652a5edd6d2c"
)
BUILDX_VERSION = "v0.34.1"
BUILDKIT_IMAGE = (
    "moby/buildkit:v0.30.0@sha256:"
    "0168606be2315b7c807a03b3d8aa79beefdb31c98740cebdffdfeebf31190c9f"
)
BLOCKED_CLAIMS = (
    "byte_identical_reproducible_image",
    "external_attestation_verified",
    "production_source_ingestion",
    "production_source_sandbox",
    "public_registry_image",
)
REQUIRED_CONTROLS = (
    "archive_verified_before_attestation",
    "base_image_digest_pinned",
    "build_context_allowlisted",
    "buildkit_cdi_disabled",
    "buildkit_image_digest_pinned",
    "buildkit_insecure_entitlements_disabled",
    "buildx_action_sha_pinned",
    "buildx_version_pinned",
    "checksum_manifest_configured",
    "ci_toolchain_hash_locked",
    "github_oidc_attestation_configured",
    "github_attestation_cli_policy_configured",
    "github_cli_version_recorded",
    "requirements_hash_locked",
    "same_run_verification_receipt_configured",
    "worker_sbom_attestation_configured",
)
_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github/workflows/release-artifacts.yml"
_MATERIALS = {
    "build_context_policy": _ROOT / ".dockerignore",
    "dockerfile": _ROOT / "docker/source-worker/Dockerfile",
    "ci_toolchain_lock": _ROOT / "requirements/ci.txt",
    "requirements": _ROOT / "requirements/source-worker.txt",
    "sbom_generator": _ROOT / "scripts/generate_source_worker_sbom.py",
    "worker_source": _ROOT / "src/tuc/frontend/_isolated_source_ingestion_worker.py",
    "archive_verifier": _ROOT / "scripts/verify_source_worker_oci_archive.py",
    "attestation_receipt_writer": (
        _ROOT / "scripts/write_github_attestation_verification_receipt.py"
    ),
    "attestation_receipt_schema": (
        _ROOT / "schemas/github_attestation_verification_receipt.v0.schema.json"
    ),
}
_OCI_PROOF = _ROOT / "tests/golden/frontend/oci_source_ingestion_research_proof_report.json"
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_BUILD_CONTEXT_ALLOWLIST = (
    "*",
    "!docker/",
    "!docker/**",
    "!requirements/",
    "!requirements/**",
    "!src/",
    "!src/**",
)
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_format",
        "artifact_name",
        "artifact_policy",
        "attest_action",
        "attested_release_artifact_configured",
        "blocked_claims",
        "buildkit_image",
        "buildx_action",
        "buildx_version",
        "execution_permission",
        "external_attestation_verified",
        "long_lived_signing_secret_required",
        "material_digests",
        "oci_research_proof_digest",
        "platform",
        "production_source_ingestion",
        "production_source_sandbox",
        "published_worker_image_provenance",
        "readiness_claim",
        "readiness_contract",
        "readiness_status",
        "report_digest",
        "required_controls",
        "sbom_format",
        "schema_version",
        "same_run_attestation_verification_configured",
        "workflow_digest",
    }
)


def build_report() -> str:
    """Return deterministic readiness evidence for the attested OCI release path."""

    workflow = _WORKFLOW.read_text(encoding="utf-8")
    _assert_release_workflow(workflow)
    _assert_build_materials()
    proof_text = _OCI_PROOF.read_text(encoding="utf-8")
    proof = _json_object(proof_text, "OCI research proof")
    if proof.get("proof_status") != "PASS":
        raise ValueError("OCI research proof did not pass")
    if proof.get("published_worker_image_provenance") is not False:
        raise ValueError("OCI research proof provenance boundary drift")
    report: dict[str, object] = {
        "artifact_format": ARTIFACT_FORMAT,
        "artifact_name": ARTIFACT_NAME,
        "artifact_policy": "metadata_digest_only_source_and_archive_omitted",
        "attest_action": ATTEST_ACTION,
        "attested_release_artifact_configured": True,
        "blocked_claims": list(BLOCKED_CLAIMS),
        "buildkit_image": BUILDKIT_IMAGE,
        "buildx_action": BUILDX_ACTION,
        "buildx_version": BUILDX_VERSION,
        "execution_permission": False,
        "external_attestation_verified": False,
        "long_lived_signing_secret_required": False,
        "material_digests": {
            name: _digest(path.read_bytes()) for name, path in sorted(_MATERIALS.items())
        },
        "oci_research_proof_digest": _digest(proof_text.encode("utf-8")),
        "platform": PLATFORM,
        "production_source_ingestion": False,
        "production_source_sandbox": False,
        "published_worker_image_provenance": False,
        "readiness_claim": READINESS_CLAIM,
        "readiness_contract": READINESS_CONTRACT,
        "readiness_status": READINESS_STATUS,
        "required_controls": list(REQUIRED_CONTROLS),
        "sbom_format": SBOM_FORMAT,
        "schema_version": SCHEMA_VERSION,
        "same_run_attestation_verification_configured": True,
        "workflow_digest": _digest(workflow.encode("utf-8")),
    }
    report["report_digest"] = _digest(_canonical_json(report).encode("utf-8"))
    assert_report_contract(report)
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def assert_report_contract(report: object) -> None:
    """Fail closed unless the readiness report matches the v0 contract."""

    if not isinstance(report, Mapping) or frozenset(report) != _TOP_LEVEL_KEYS:
        raise ValueError("OCI release provenance readiness report shape rejected")
    expected = {
        "artifact_format": ARTIFACT_FORMAT,
        "artifact_name": ARTIFACT_NAME,
        "artifact_policy": "metadata_digest_only_source_and_archive_omitted",
        "attest_action": ATTEST_ACTION,
        "attested_release_artifact_configured": True,
        "blocked_claims": list(BLOCKED_CLAIMS),
        "buildkit_image": BUILDKIT_IMAGE,
        "buildx_action": BUILDX_ACTION,
        "buildx_version": BUILDX_VERSION,
        "execution_permission": False,
        "external_attestation_verified": False,
        "long_lived_signing_secret_required": False,
        "platform": PLATFORM,
        "production_source_ingestion": False,
        "production_source_sandbox": False,
        "published_worker_image_provenance": False,
        "readiness_claim": READINESS_CLAIM,
        "readiness_contract": READINESS_CONTRACT,
        "readiness_status": READINESS_STATUS,
        "required_controls": list(REQUIRED_CONTROLS),
        "sbom_format": SBOM_FORMAT,
        "schema_version": SCHEMA_VERSION,
        "same_run_attestation_verification_configured": True,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError(f"OCI release provenance readiness {key} drift")
    materials = report.get("material_digests")
    if not isinstance(materials, Mapping) or tuple(materials) != tuple(sorted(_MATERIALS)):
        raise ValueError("OCI release provenance material set drift")
    for digest in materials.values():
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise ValueError("OCI release provenance material digest drift")
    for key in ("oci_research_proof_digest", "workflow_digest", "report_digest"):
        digest = report.get(key)
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise ValueError(f"OCI release provenance {key} drift")
    unsigned = dict(report)
    report_digest = unsigned.pop("report_digest")
    if report_digest != _digest(_canonical_json(unsigned).encode("utf-8")):
        raise ValueError("OCI release provenance report digest mismatch")
    serialized = _canonical_json(report).lower()
    for fragment in (
        "@triton.jit",
        '"archive_bytes"',
        '"command_line"',
        '"host_path"',
        '"raw_source"',
        '"source_text"',
    ):
        if fragment in serialized:
            raise ValueError("OCI release provenance report leaked forbidden material")


def _assert_release_workflow(workflow: str) -> None:
    if not workflow or len(workflow.encode("utf-8")) > 64 * 1024:
        raise ValueError("release workflow bounds rejected")
    required = (
        "permissions:\n  contents: read",
        "id-token: write",
        "attestations: write",
        BUILDX_ACTION,
        f"version: {BUILDX_VERSION}",
        f"driver-opts: image={BUILDKIT_IMAGE}",
        "buildkitd-flags: --cdi-disabled",
        ATTEST_ACTION,
        "--platform linux/amd64",
        "--provenance=false",
        "--sbom=false",
        "type=oci,dest=dist/tuc-source-ingestion-worker.oci.tar",
        "scripts/verify_source_worker_oci_archive.py",
        "scripts/generate_source_worker_sbom.py",
        "python -m pip install --require-hashes -r requirements/ci.txt",
        "python -m pip install --no-deps --no-build-isolation -e .",
        "PYTHONPATH: ${{ github.workspace }}",
        "gh attestation verify dist/tuc-source-ingestion-worker.oci.tar",
        '--repo "$GITHUB_REPOSITORY"',
        '--signer-workflow "$GITHUB_REPOSITORY/.github/workflows/release-artifacts.yml"',
        '--source-digest "$GITHUB_SHA"',
        '--source-ref "$GITHUB_REF"',
        '--cert-oidc-issuer "https://token.actions.githubusercontent.com"',
        '--predicate-type "https://slsa.dev/provenance/v1"',
        "--deny-self-hosted-runners",
        "--limit 8",
        '--format json >"$RUNNER_TEMP/tuc-worker-attestation-verification.json"',
        "scripts/write_github_attestation_verification_receipt.py",
        '--verification-result "$RUNNER_TEMP/tuc-worker-attestation-verification.json"',
        "dist/*.attestation-verification.json",
        "subject-path: dist/tuc-source-ingestion-worker.oci.tar",
        "sbom-path: dist/tuc-source-ingestion-worker.cdx.json",
        "dist/*.oci-verification.json",
        "dist/*.oci.tar",
    )
    if any(fragment not in workflow for fragment in required):
        raise ValueError("release workflow OCI provenance control missing")
    if workflow.count("subject-path: dist/tuc-source-ingestion-worker.oci.tar") != 2:
        raise ValueError("release workflow OCI attestation cardinality drift")
    if workflow.count("gh attestation verify") != 1:
        raise ValueError("release workflow OCI verification cardinality drift")
    if "--signer-repo" in workflow:
        raise ValueError("release workflow incompatible signer identity flags")
    if workflow.count("--signer-workflow") != 1:
        raise ValueError("release workflow signer identity cardinality drift")
    if not (
        workflow.index("scripts/verify_source_worker_oci_archive.py")
        < workflow.index("Attest source-worker OCI provenance")
        < workflow.index("gh attestation verify")
        < workflow.index("scripts/write_github_attestation_verification_receipt.py")
        < workflow.index("scripts/write_artifact_checksums.py")
        < workflow.index("Upload release artifact bundle")
    ):
        raise ValueError("release workflow OCI verification order drift")
    if "--allow-insecure-entitlement" in workflow:
        raise ValueError("release workflow insecure BuildKit entitlement rejected")
    if "pull_request_target:" in workflow or "pull_request:" in workflow:
        raise ValueError("release workflow untrusted trigger rejected")


def _assert_build_materials() -> None:
    dockerfile = _MATERIALS["dockerfile"].read_text(encoding="utf-8")
    requirements = _MATERIALS["requirements"].read_text(encoding="utf-8")
    ignore = _MATERIALS["build_context_policy"].read_text(encoding="utf-8")
    if re.search(r"^FROM [^\n]+@sha256:[a-f0-9]{64}$", dockerfile, re.MULTILINE) is None:
        raise ValueError("source worker base image is not digest pinned")
    if re.fullmatch(
        r"numpy==2\.4\.4 --hash=sha256:[a-f0-9]{64}\n?",
        requirements,
    ) is None:
        raise ValueError("source worker requirement lock rejected")
    if tuple(ignore.splitlines()) != _BUILD_CONTEXT_ALLOWLIST:
        raise ValueError("source worker build context policy rejected")


def _json_object(text: str, label: str) -> Mapping[str, object]:
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"{label} JSON rejected") from exc
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} must be object")
    return payload


def _digest(data: bytes) -> str:
    return f"sha256:{sha256(data).hexdigest()}"


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
