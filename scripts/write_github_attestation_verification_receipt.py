"""Write a bounded receipt after GitHub CLI attestation verification succeeds."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA_VERSION = "tuc.github_attestation_verification_receipt.v0"
VERIFICATION_CONTRACT = "github_attestation.same_run.provenance_verified.v0"
ARTIFACT_NAME = "tuc-source-ingestion-worker.oci.tar"
RECEIPT_NAME = "tuc-source-ingestion-worker.attestation-verification.json"
PREDICATE_TYPE = "https://slsa.dev/provenance/v1"
OIDC_ISSUER = "https://token.actions.githubusercontent.com"
WORKFLOW_PATH = ".github/workflows/release-artifacts.yml"
VERIFICATION_POLICY = (
    "repository_signer_workflow_source_commit_source_ref_oidc_issuer_"
    "github_hosted_runner_bound"
)
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024 * 1024
MAX_RECEIPT_BYTES = 8 * 1024
MAX_VERIFICATION_RESULT_BYTES = 512 * 1024
MAX_VERIFIED_ATTESTATIONS = 8
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_COMMIT_RE = re.compile(r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
_REF_RE = re.compile(r"^refs/(?:heads|tags)/[A-Za-z0-9._/-]{1,240}$")
_GH_VERSION_RE = re.compile(r"^gh version [0-9]+\.[0-9]+\.[0-9]+[^\r\n]{0,120}$")


def build_receipt(
    artifact: Path,
    *,
    verification_result: object,
    repository: str,
    source_commit: str,
    source_ref: str,
    event_name: str,
    run_id: int,
    run_attempt: int,
    runner_environment: str,
    gh_version: str,
) -> dict[str, object]:
    """Build a digest-bound receipt from trusted GitHub workflow context."""

    artifact_path = _validate_artifact(artifact)
    artifact_digest = _sha256(artifact_path)
    verified_attestation_count = _validate_verification_result(
        verification_result,
        artifact_digest,
    )
    _validate_context(
        repository=repository,
        source_commit=source_commit,
        source_ref=source_ref,
        event_name=event_name,
        run_id=run_id,
        run_attempt=run_attempt,
        runner_environment=runner_environment,
        gh_version=gh_version,
    )
    release_tag_trigger = event_name == "push" and source_ref.startswith("refs/tags/v")
    report: dict[str, object] = {
        "artifact_bytes_omitted": True,
        "artifact_digest": artifact_digest,
        "artifact_name": ARTIFACT_NAME,
        "artifact_size_bytes": artifact_path.stat().st_size,
        "attestation_bundle_omitted": True,
        "attestation_verified": True,
        "event_name": event_name,
        "execution_permission": False,
        "external_consumer_verification": False,
        "gh_version": gh_version,
        "oidc_issuer": OIDC_ISSUER,
        "predicate_type": PREDICATE_TYPE,
        "production_source_ingestion": False,
        "production_source_sandbox": False,
        "protected_tag_policy_verified": False,
        "public_registry_image": False,
        "raw_verification_output_omitted": True,
        "receipt_trust_boundary": "generated_only_after_cli_exit_zero_not_self_authenticating",
        "repository": repository,
        "release_tag_trigger": release_tag_trigger,
        "run_attempt": run_attempt,
        "run_id": run_id,
        "runner_environment": runner_environment,
        "schema_version": SCHEMA_VERSION,
        "signer_repository": repository,
        "signer_workflow": f"{repository}/{WORKFLOW_PATH}",
        "source_commit": source_commit,
        "source_ref": source_ref,
        "verification_contract": VERIFICATION_CONTRACT,
        "verification_policy": VERIFICATION_POLICY,
        "verification_scope": "same_run_repository_attestation_api",
        "verification_status": "PASS",
        "verified_attestation_count": verified_attestation_count,
        "workflow_run_url": f"https://github.com/{repository}/actions/runs/{run_id}",
    }
    report["report_digest"] = _digest(_canonical_json(report).encode("utf-8"))
    return report


def write_receipt(
    artifact: Path,
    output: Path,
    *,
    verification_result_path: Path,
    repository: str,
    source_commit: str,
    source_ref: str,
    event_name: str,
    run_id: int,
    run_attempt: int,
    runner_environment: str,
    gh_version: str,
) -> dict[str, object]:
    """Write one receipt beside the verified artifact without following symlinks."""

    artifact_path = _validate_artifact(artifact)
    output_parent = output.parent.resolve(strict=True)
    if output.name != RECEIPT_NAME or output_parent != artifact_path.parent:
        raise ValueError("attestation verification receipt output path rejected")
    if output.exists() or output.is_symlink():
        raise ValueError("attestation verification receipt output already exists")
    verification_result = _load_verification_result(verification_result_path)
    report = build_receipt(
        artifact_path,
        verification_result=verification_result,
        repository=repository,
        source_commit=source_commit,
        source_ref=source_ref,
        event_name=event_name,
        run_id=run_id,
        run_attempt=run_attempt,
        runner_environment=runner_environment,
        gh_version=gh_version,
    )
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if len(serialized.encode("utf-8")) > MAX_RECEIPT_BYTES:
        raise ValueError("attestation verification receipt exceeds byte limit")
    with output.open("x", encoding="utf-8", newline="\n") as receipt:
        receipt.write(serialized)
    return report


def _validate_artifact(artifact: Path) -> Path:
    if artifact.name != ARTIFACT_NAME or artifact.is_symlink():
        raise ValueError("attestation verification artifact path rejected")
    try:
        artifact_path = artifact.resolve(strict=True)
    except OSError as exc:
        raise ValueError("attestation verification artifact unavailable") from exc
    if not artifact_path.is_file():
        raise ValueError("attestation verification artifact must be a regular file")
    size = artifact_path.stat().st_size
    if size <= 0 or size > MAX_ARTIFACT_BYTES:
        raise ValueError("attestation verification artifact size rejected")
    return artifact_path


def _validate_context(
    *,
    repository: str,
    source_commit: str,
    source_ref: str,
    event_name: str,
    run_id: int,
    run_attempt: int,
    runner_environment: str,
    gh_version: str,
) -> None:
    if _REPOSITORY_RE.fullmatch(repository) is None:
        raise ValueError("attestation verification repository rejected")
    if _COMMIT_RE.fullmatch(source_commit) is None:
        raise ValueError("attestation verification source commit rejected")
    if (
        _REF_RE.fullmatch(source_ref) is None
        or ".." in source_ref
        or "//" in source_ref
    ):
        raise ValueError("attestation verification source ref rejected")
    if event_name not in {"push", "workflow_dispatch"}:
        raise ValueError("attestation verification event rejected")
    if isinstance(run_id, bool) or not isinstance(run_id, int) or not 0 < run_id < 2**63:
        raise ValueError("attestation verification run id rejected")
    if (
        isinstance(run_attempt, bool)
        or not isinstance(run_attempt, int)
        or not 0 < run_attempt <= 100
    ):
        raise ValueError("attestation verification run attempt rejected")
    if runner_environment != "github-hosted":
        raise ValueError("attestation verification runner environment rejected")
    if _GH_VERSION_RE.fullmatch(gh_version) is None:
        raise ValueError("attestation verification GitHub CLI version rejected")


def _load_verification_result(path: Path) -> object:
    if path.is_symlink():
        raise ValueError("attestation verification result path rejected")
    try:
        result_path = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError("attestation verification result unavailable") from exc
    if not result_path.is_file():
        raise ValueError("attestation verification result must be a regular file")
    size = result_path.stat().st_size
    if size <= 0 or size > MAX_VERIFICATION_RESULT_BYTES:
        raise ValueError("attestation verification result size rejected")
    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("attestation verification result JSON rejected") from exc


def _validate_verification_result(result: object, artifact_digest: str) -> int:
    if (
        not isinstance(result, list)
        or not result
        or len(result) > MAX_VERIFIED_ATTESTATIONS
    ):
        raise ValueError("attestation verification result cardinality rejected")
    expected_digest = artifact_digest.removeprefix("sha256:")
    for entry in result:
        if not isinstance(entry, dict) or frozenset(entry) != {
            "attestation",
            "verificationResult",
        }:
            raise ValueError("attestation verification result shape rejected")
        verification = entry.get("verificationResult")
        if not isinstance(verification, dict):
            raise ValueError("attestation verification result shape rejected")
        statement = verification.get("statement")
        if not isinstance(statement, dict):
            raise ValueError("attestation verification statement rejected")
        if statement.get("predicateType") != PREDICATE_TYPE:
            raise ValueError("attestation verification predicate rejected")
        subjects = statement.get("subject")
        if not isinstance(subjects, list) or not 0 < len(subjects) <= 32:
            raise ValueError("attestation verification subject cardinality rejected")
        if not any(_subject_matches(subject, expected_digest) for subject in subjects):
            raise ValueError("attestation verification subject digest rejected")
    return len(result)


def _subject_matches(subject: object, expected_digest: str) -> bool:
    if not isinstance(subject, dict):
        return False
    name = subject.get("name")
    digest = subject.get("digest")
    return (
        isinstance(name, str)
        and 0 < len(name) <= 512
        and ".." not in name
        and name.replace("\\", "/").rsplit("/", 1)[-1] == ARTIFACT_NAME
        and isinstance(digest, dict)
        and digest.get("sha256") == expected_digest
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verification-result", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--runner-environment", required=True)
    parser.add_argument("--gh-version", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    write_receipt(
        args.artifact,
        args.output,
        verification_result_path=args.verification_result,
        repository=args.repository,
        source_commit=args.source_commit,
        source_ref=args.source_ref,
        event_name=args.event_name,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        runner_environment=args.runner_environment,
        gh_version=args.gh_version,
    )


if __name__ == "__main__":
    main()
