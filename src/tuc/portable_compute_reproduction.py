"""Deterministic data-only reproduction kit for Objective Delta."""

from __future__ import annotations

import json
import math
import re
import stat
import sys
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

from tuc.portable_compute import (
    PORTABLE_COMPUTE_BLOCKED_CLAIMS,
    PORTABLE_COMPUTE_PROOF_CONTRACT,
    PORTABLE_COMPUTE_PUBLIC_API_VERSION,
    PortableComputeProofError,
    assert_portable_compute_proof_report,
    dump_portable_compute_proof,
)
from tuc.report_output import (
    PublicReportOutputError,
    emit_public_json_report,
    emit_public_text_report,
)

PORTABLE_COMPUTE_REPRODUCTION_PUBLIC_API_VERSION = (
    "tuc.portable_compute_reproduction_public_api.v0"
)
PORTABLE_COMPUTE_REPRODUCTION_CLI_NAME = "tuc-reproduce-portable-compute"
PORTABLE_COMPUTE_REPRODUCTION_KIT_SCHEMA_VERSION = (
    "tuc.portable_compute_reproduction_kit_manifest.v0"
)
PORTABLE_COMPUTE_REPRODUCTION_KIT_CONTRACT = (
    "portable_compute.reproduction_kit.data_only.v0"
)
PORTABLE_COMPUTE_REPRODUCTION_RECEIPT_SCHEMA_VERSION = (
    "tuc.portable_compute_reproduction_receipt.v0"
)
PORTABLE_COMPUTE_REPRODUCTION_CONTRACT = (
    "portable_compute.reproduction.installed_offline.v0"
)
PORTABLE_COMPUTE_REPRODUCTION_KIT_ID = "objective_delta_installed_portable_compute"
PORTABLE_COMPUTE_REPRODUCTION_STATUS = "PASS"
PORTABLE_COMPUTE_REPRODUCTION_ARCHIVE_POLICY = (
    "exact_stored_members_regular_non_executable_digest_bound.v0"
)
PORTABLE_COMPUTE_REPRODUCTION_MEMBER_POLICY = "data_only_no_executable_content"

MAX_REPRODUCTION_ARCHIVE_BYTES = 256 * 1024
MAX_REPRODUCTION_MEMBER_BYTES = 64 * 1024
MAX_REPRODUCTION_TOTAL_MEMBER_BYTES = 192 * 1024
MAX_REPRODUCTION_MANIFEST_DEPTH = 8
MAX_REPRODUCTION_MANIFEST_ITEMS = 128
MAX_REPRODUCTION_MANIFEST_STRING_BYTES = 512

REPRODUCTION_MANIFEST_PATH = "manifest.json"
REPRODUCTION_PAYLOAD_SPECS = (
    ("source_intent.v0.json", "source_intent"),
    ("external_systolic.v0.json", "backend_package_systolic"),
    ("external_vector.v0.json", "backend_package_vector"),
    ("expected_report.json", "portable_compute_expected_report"),
)
REPRODUCTION_PAYLOAD_PATHS = tuple(path for path, _role in REPRODUCTION_PAYLOAD_SPECS)
REPRODUCTION_MEMBER_PATHS = (REPRODUCTION_MANIFEST_PATH, *REPRODUCTION_PAYLOAD_PATHS)
REPRODUCTION_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

_CLI_USAGE = "usage: tuc-reproduce-portable-compute KIT.zip\n"
_CLI_REJECTION = "tuc-reproduce-portable-compute: kit rejected\n"
_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_MANIFEST_KEYS = frozenset(
    {
        "archive_policy",
        "blocked_claims",
        "executable_content_included",
        "files",
        "independent_reproduction_claim",
        "kit_contract",
        "kit_id",
        "member_policy",
        "native_performance_claim",
        "portable_compute_proof_contract",
        "portable_compute_public_api_version",
        "reproduction_public_api_version",
        "schema_version",
    }
)
_MANIFEST_FILE_KEYS = frozenset(
    {"content_type", "path", "role", "sha256", "size_bytes"}
)
_RECEIPT_KEYS = frozenset(
    {
        "archive_policy",
        "backend_equivalence_passed",
        "blocked_claims",
        "expected_report_digest",
        "external_package_code_executed",
        "external_plugin_execution",
        "fallback_assignment_count",
        "independent_reproduction_claim",
        "kit_contract",
        "kit_digest",
        "kit_id",
        "layout_conversion_count",
        "manifest_digest",
        "native_performance_claim",
        "observed_report_digest",
        "package_digests",
        "package_ids",
        "portable_compute_proof_contract",
        "portable_compute_proof_status",
        "portable_compute_public_api_version",
        "raw_tensor_values_serialized",
        "reference_correctness_passed",
        "reports_byte_identical",
        "reproduction_contract",
        "reproduction_public_api_version",
        "reproduction_status",
        "schema_version",
        "source_intent_payload_serialized",
        "source_text_executed",
        "trusted_executor_sequence",
        "verified_payload_file_count",
        "verified_payload_file_names",
    }
)


class PortableComputeReproductionError(ValueError):
    """Raised when a reproduction kit or receipt fails closed."""


def build_portable_compute_reproduction_kit(
    consumer_directory: str | Path,
    output_path: str | Path,
) -> str:
    """Build one deterministic Objective Delta data-only ZIP archive."""

    consumer = _resolve_directory(consumer_directory, "consumer directory")
    output = Path(output_path)
    if output.suffix != ".zip":
        raise PortableComputeReproductionError("reproduction kit must use .zip suffix")
    if output.exists() or output.is_symlink():
        raise PortableComputeReproductionError("reproduction kit output must not exist")
    parent = output.parent.resolve(strict=True)
    if not parent.is_dir() or parent.is_symlink():
        raise PortableComputeReproductionError("reproduction kit output parent invalid")
    resolved_output = parent / output.name

    payloads = {
        path: _read_regular_bounded_file(
            consumer / path,
            label=role,
            max_bytes=MAX_REPRODUCTION_MEMBER_BYTES,
        )
        for path, role in REPRODUCTION_PAYLOAD_SPECS
    }
    expected_report = _json_object(payloads["expected_report.json"], "expected report")
    assert_portable_compute_proof_report(expected_report)
    try:
        observed_report = dump_portable_compute_proof(
            consumer / "source_intent.v0.json",
            (
                consumer / "external_systolic.v0.json",
                consumer / "external_vector.v0.json",
            ),
        ).encode("utf-8")
    except (OSError, TypeError, ValueError) as exc:
        raise PortableComputeReproductionError(
            "reproduction kit source evidence invalid"
        ) from exc
    if observed_report != payloads["expected_report.json"]:
        raise PortableComputeReproductionError(
            "reproduction kit source evidence does not reproduce expected report"
        )
    manifest = _build_manifest(payloads)
    manifest_bytes = _dump_json(manifest)

    try:
        with zipfile.ZipFile(
            resolved_output,
            mode="x",
            compression=zipfile.ZIP_STORED,
            allowZip64=False,
        ) as archive:
            archive.comment = b""
            for member_name in REPRODUCTION_MEMBER_PATHS:
                content = (
                    manifest_bytes
                    if member_name == REPRODUCTION_MANIFEST_PATH
                    else payloads[member_name]
                )
                archive.writestr(_canonical_zip_info(member_name), content)
        _load_reproduction_kit(resolved_output)
    except Exception:
        if resolved_output.is_file() and not resolved_output.is_symlink():
            resolved_output.unlink()
        raise
    return f"sha256:{_sha256_bytes(resolved_output.read_bytes())}"


def reproduce_portable_compute(kit_path: str | Path) -> dict[str, object]:
    """Replay Objective Delta from one verified data-only reproduction kit."""

    archive_path, manifest, members = _load_reproduction_kit(kit_path)
    expected_bytes = members["expected_report.json"]
    expected_report = assert_portable_compute_proof_report(
        _json_object(expected_bytes, "expected report")
    )

    with tempfile.TemporaryDirectory(prefix="tuc-portable-compute-reproduction-") as root:
        temporary = Path(root)
        for member_name in REPRODUCTION_PAYLOAD_PATHS[:-1]:
            (temporary / member_name).write_bytes(members[member_name])
        observed_text = dump_portable_compute_proof(
            temporary / "source_intent.v0.json",
            (
                temporary / "external_systolic.v0.json",
                temporary / "external_vector.v0.json",
            ),
        )

    observed_bytes = observed_text.encode("utf-8")
    if observed_bytes != expected_bytes:
        raise PortableComputeReproductionError("portable compute report drift")
    observed_report = assert_portable_compute_proof_report(
        _json_object(observed_bytes, "observed report")
    )
    if observed_report != expected_report:
        raise PortableComputeReproductionError("portable compute semantic report drift")

    receipt: dict[str, object] = {
        "archive_policy": PORTABLE_COMPUTE_REPRODUCTION_ARCHIVE_POLICY,
        "backend_equivalence_passed": observed_report["backend_equivalence_passed"],
        "blocked_claims": list(PORTABLE_COMPUTE_BLOCKED_CLAIMS),
        "expected_report_digest": _digest_bytes(expected_bytes),
        "external_package_code_executed": False,
        "external_plugin_execution": False,
        "fallback_assignment_count": observed_report["fallback_assignment_count"],
        "independent_reproduction_claim": False,
        "kit_contract": PORTABLE_COMPUTE_REPRODUCTION_KIT_CONTRACT,
        "kit_digest": _digest_bytes(archive_path.read_bytes()),
        "kit_id": PORTABLE_COMPUTE_REPRODUCTION_KIT_ID,
        "layout_conversion_count": observed_report["layout_conversion_count"],
        "manifest_digest": _digest_bytes(members[REPRODUCTION_MANIFEST_PATH]),
        "native_performance_claim": False,
        "observed_report_digest": _digest_bytes(observed_bytes),
        "package_digests": observed_report["package_digests"],
        "package_ids": observed_report["package_ids"],
        "portable_compute_proof_contract": PORTABLE_COMPUTE_PROOF_CONTRACT,
        "portable_compute_proof_status": observed_report["proof_status"],
        "portable_compute_public_api_version": PORTABLE_COMPUTE_PUBLIC_API_VERSION,
        "raw_tensor_values_serialized": False,
        "reference_correctness_passed": observed_report["reference_correctness_passed"],
        "reports_byte_identical": True,
        "reproduction_contract": PORTABLE_COMPUTE_REPRODUCTION_CONTRACT,
        "reproduction_public_api_version": (
            PORTABLE_COMPUTE_REPRODUCTION_PUBLIC_API_VERSION
        ),
        "reproduction_status": PORTABLE_COMPUTE_REPRODUCTION_STATUS,
        "schema_version": PORTABLE_COMPUTE_REPRODUCTION_RECEIPT_SCHEMA_VERSION,
        "source_intent_payload_serialized": False,
        "source_text_executed": False,
        "trusted_executor_sequence": observed_report["trusted_executor_sequence"],
        "verified_payload_file_count": len(REPRODUCTION_PAYLOAD_PATHS),
        "verified_payload_file_names": list(REPRODUCTION_PAYLOAD_PATHS),
    }
    assert_portable_compute_reproduction_receipt(receipt)
    _assert_manifest_matches_receipt(manifest, receipt)
    return receipt


def dump_portable_compute_reproduction_receipt(kit_path: str | Path) -> str:
    """Return one stable metadata-only reproduction receipt."""

    return json.dumps(
        reproduce_portable_compute(kit_path),
        indent=2,
        sort_keys=True,
    ) + "\n"


def emit_portable_compute_reproduction_receipt(kit_path: str | Path) -> None:
    """Emit a verified receipt through TUC's public report boundary."""

    emit_public_json_report(dump_portable_compute_reproduction_receipt(kit_path))


def assert_portable_compute_reproduction_receipt(report: object) -> None:
    """Fail closed unless a receipt matches the exact Objective Delta v0 contract."""

    if type(report) is not dict:
        raise PortableComputeReproductionError("reproduction receipt must be plain object")
    normalized = cast(dict[str, object], report)
    if frozenset(normalized) != _RECEIPT_KEYS:
        raise PortableComputeReproductionError("reproduction receipt key drift")
    expected: dict[str, object] = {
        "archive_policy": PORTABLE_COMPUTE_REPRODUCTION_ARCHIVE_POLICY,
        "backend_equivalence_passed": True,
        "blocked_claims": list(PORTABLE_COMPUTE_BLOCKED_CLAIMS),
        "external_package_code_executed": False,
        "external_plugin_execution": False,
        "fallback_assignment_count": 0,
        "independent_reproduction_claim": False,
        "kit_contract": PORTABLE_COMPUTE_REPRODUCTION_KIT_CONTRACT,
        "kit_id": PORTABLE_COMPUTE_REPRODUCTION_KIT_ID,
        "layout_conversion_count": 1,
        "native_performance_claim": False,
        "portable_compute_proof_contract": PORTABLE_COMPUTE_PROOF_CONTRACT,
        "portable_compute_proof_status": "PASS",
        "portable_compute_public_api_version": PORTABLE_COMPUTE_PUBLIC_API_VERSION,
        "raw_tensor_values_serialized": False,
        "reference_correctness_passed": True,
        "reports_byte_identical": True,
        "reproduction_contract": PORTABLE_COMPUTE_REPRODUCTION_CONTRACT,
        "reproduction_public_api_version": (
            PORTABLE_COMPUTE_REPRODUCTION_PUBLIC_API_VERSION
        ),
        "reproduction_status": PORTABLE_COMPUTE_REPRODUCTION_STATUS,
        "schema_version": PORTABLE_COMPUTE_REPRODUCTION_RECEIPT_SCHEMA_VERSION,
        "source_intent_payload_serialized": False,
        "source_text_executed": False,
        "trusted_executor_sequence": ["systolic-sim", "vector-sim"],
        "verified_payload_file_count": len(REPRODUCTION_PAYLOAD_PATHS),
        "verified_payload_file_names": list(REPRODUCTION_PAYLOAD_PATHS),
    }
    for key, expected_value in expected.items():
        if normalized[key] != expected_value:
            raise PortableComputeReproductionError(f"reproduction receipt {key} drift")
    if normalized["expected_report_digest"] != normalized["observed_report_digest"]:
        raise PortableComputeReproductionError("reproduction receipt report digest drift")
    for key in (
        "expected_report_digest",
        "kit_digest",
        "manifest_digest",
        "observed_report_digest",
    ):
        _assert_digest(normalized[key], key)
    _assert_string_list(normalized["package_ids"], "package_ids", expected_count=2)
    package_digests = _assert_string_list(
        normalized["package_digests"], "package_digests", expected_count=2
    )
    for digest in package_digests:
        _assert_digest(digest, "package digest")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the installed Objective Delta reproduction CLI."""

    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if arguments == ("--help",):
        emit_public_text_report(_CLI_USAGE)
        return 0
    if len(arguments) != 1:
        sys.stderr.write(_CLI_USAGE)
        return 2
    try:
        emit_portable_compute_reproduction_receipt(arguments[0])
    except (
        OSError,
        PortableComputeProofError,
        PortableComputeReproductionError,
        PublicReportOutputError,
        TypeError,
        UnicodeError,
        ValueError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
    ):
        sys.stderr.write(_CLI_REJECTION)
        return 2
    return 0


def _build_manifest(payloads: Mapping[str, bytes]) -> dict[str, object]:
    files = [
        {
            "content_type": "application/json",
            "path": path,
            "role": role,
            "sha256": _digest_bytes(payloads[path]),
            "size_bytes": len(payloads[path]),
        }
        for path, role in REPRODUCTION_PAYLOAD_SPECS
    ]
    manifest: dict[str, object] = {
        "archive_policy": PORTABLE_COMPUTE_REPRODUCTION_ARCHIVE_POLICY,
        "blocked_claims": list(PORTABLE_COMPUTE_BLOCKED_CLAIMS),
        "executable_content_included": False,
        "files": files,
        "independent_reproduction_claim": False,
        "kit_contract": PORTABLE_COMPUTE_REPRODUCTION_KIT_CONTRACT,
        "kit_id": PORTABLE_COMPUTE_REPRODUCTION_KIT_ID,
        "member_policy": PORTABLE_COMPUTE_REPRODUCTION_MEMBER_POLICY,
        "native_performance_claim": False,
        "portable_compute_proof_contract": PORTABLE_COMPUTE_PROOF_CONTRACT,
        "portable_compute_public_api_version": PORTABLE_COMPUTE_PUBLIC_API_VERSION,
        "reproduction_public_api_version": (
            PORTABLE_COMPUTE_REPRODUCTION_PUBLIC_API_VERSION
        ),
        "schema_version": PORTABLE_COMPUTE_REPRODUCTION_KIT_SCHEMA_VERSION,
    }
    _assert_manifest(manifest, payloads)
    return manifest


def _load_reproduction_kit(
    kit_path: str | Path,
) -> tuple[Path, dict[str, object], dict[str, bytes]]:
    archive_path = _resolve_regular_file(kit_path, "reproduction kit")
    if archive_path.suffix != ".zip":
        raise PortableComputeReproductionError("reproduction kit must use .zip suffix")
    if archive_path.stat().st_size > MAX_REPRODUCTION_ARCHIVE_BYTES:
        raise PortableComputeReproductionError("reproduction kit exceeds byte limit")
    with zipfile.ZipFile(archive_path, mode="r", allowZip64=False) as archive:
        if archive.comment:
            raise PortableComputeReproductionError("reproduction kit comment forbidden")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(infos) != len(REPRODUCTION_MEMBER_PATHS) or len(set(names)) != len(names):
            raise PortableComputeReproductionError("reproduction kit member count drift")
        if tuple(names) != REPRODUCTION_MEMBER_PATHS:
            raise PortableComputeReproductionError("reproduction kit member order drift")
        total_bytes = 0
        members: dict[str, bytes] = {}
        for info in infos:
            _assert_zip_info(info)
            total_bytes += info.file_size
            if total_bytes > MAX_REPRODUCTION_TOTAL_MEMBER_BYTES:
                raise PortableComputeReproductionError(
                    "reproduction kit expanded size exceeds limit"
                )
            content = archive.read(info)
            if len(content) != info.file_size:
                raise PortableComputeReproductionError("reproduction kit member size drift")
            members[info.filename] = content
    manifest = _json_object(members[REPRODUCTION_MANIFEST_PATH], "manifest")
    _assert_manifest(manifest, members)
    return archive_path, manifest, members


def _assert_zip_info(info: zipfile.ZipInfo) -> None:
    if info.filename not in REPRODUCTION_MEMBER_PATHS:
        raise PortableComputeReproductionError("reproduction kit member forbidden")
    if info.filename.startswith(("/", "\\")) or "\\" in info.filename:
        raise PortableComputeReproductionError("reproduction kit member path invalid")
    if any(part in {"", ".", ".."} for part in Path(info.filename).parts):
        raise PortableComputeReproductionError("reproduction kit member path invalid")
    if info.is_dir() or info.flag_bits & 0x1:
        raise PortableComputeReproductionError("reproduction kit member type forbidden")
    if info.compress_type != zipfile.ZIP_STORED or info.compress_size != info.file_size:
        raise PortableComputeReproductionError("reproduction kit compression forbidden")
    if info.file_size > MAX_REPRODUCTION_MEMBER_BYTES:
        raise PortableComputeReproductionError("reproduction kit member exceeds byte limit")
    if info.date_time != REPRODUCTION_ZIP_TIMESTAMP or info.extra or info.comment:
        raise PortableComputeReproductionError("reproduction kit metadata drift")
    mode = info.external_attr >> 16
    if info.create_system != 3 or stat.S_IFMT(mode) != stat.S_IFREG:
        raise PortableComputeReproductionError("reproduction kit member must be regular file")
    if mode & 0o111 or stat.S_IMODE(mode) != 0o644:
        raise PortableComputeReproductionError("reproduction kit executable member forbidden")


def _assert_manifest(
    manifest: object,
    members: Mapping[str, bytes],
) -> None:
    if type(manifest) is not dict:
        raise PortableComputeReproductionError("reproduction manifest must be plain object")
    normalized = cast(dict[str, object], manifest)
    if frozenset(normalized) != _MANIFEST_KEYS:
        raise PortableComputeReproductionError("reproduction manifest key drift")
    expected: dict[str, object] = {
        "archive_policy": PORTABLE_COMPUTE_REPRODUCTION_ARCHIVE_POLICY,
        "blocked_claims": list(PORTABLE_COMPUTE_BLOCKED_CLAIMS),
        "executable_content_included": False,
        "independent_reproduction_claim": False,
        "kit_contract": PORTABLE_COMPUTE_REPRODUCTION_KIT_CONTRACT,
        "kit_id": PORTABLE_COMPUTE_REPRODUCTION_KIT_ID,
        "member_policy": PORTABLE_COMPUTE_REPRODUCTION_MEMBER_POLICY,
        "native_performance_claim": False,
        "portable_compute_proof_contract": PORTABLE_COMPUTE_PROOF_CONTRACT,
        "portable_compute_public_api_version": PORTABLE_COMPUTE_PUBLIC_API_VERSION,
        "reproduction_public_api_version": (
            PORTABLE_COMPUTE_REPRODUCTION_PUBLIC_API_VERSION
        ),
        "schema_version": PORTABLE_COMPUTE_REPRODUCTION_KIT_SCHEMA_VERSION,
    }
    for key, expected_value in expected.items():
        if normalized[key] != expected_value:
            raise PortableComputeReproductionError(f"reproduction manifest {key} drift")
    files = normalized["files"]
    if type(files) is not list or len(files) != len(REPRODUCTION_PAYLOAD_SPECS):
        raise PortableComputeReproductionError("reproduction manifest file count drift")
    for item, (expected_path, expected_role) in zip(
        files,
        REPRODUCTION_PAYLOAD_SPECS,
        strict=True,
    ):
        if type(item) is not dict or frozenset(item) != _MANIFEST_FILE_KEYS:
            raise PortableComputeReproductionError("reproduction manifest file entry drift")
        entry = cast(dict[str, object], item)
        expected_entry = {
            "content_type": "application/json",
            "path": expected_path,
            "role": expected_role,
            "sha256": _digest_bytes(members[expected_path]),
            "size_bytes": len(members[expected_path]),
        }
        if entry != expected_entry:
            raise PortableComputeReproductionError(
                "reproduction manifest file binding drift"
            )


def _assert_manifest_matches_receipt(
    manifest: Mapping[str, object],
    receipt: Mapping[str, object],
) -> None:
    for manifest_key, receipt_key in (
        ("archive_policy", "archive_policy"),
        ("kit_contract", "kit_contract"),
        ("kit_id", "kit_id"),
        ("portable_compute_proof_contract", "portable_compute_proof_contract"),
        ("portable_compute_public_api_version", "portable_compute_public_api_version"),
        ("reproduction_public_api_version", "reproduction_public_api_version"),
    ):
        if manifest[manifest_key] != receipt[receipt_key]:
            raise PortableComputeReproductionError("manifest receipt binding drift")


def _json_object(payload: bytes, label: str) -> dict[str, object]:
    if len(payload) > MAX_REPRODUCTION_MEMBER_BYTES:
        raise PortableComputeReproductionError(f"{label} exceeds byte limit")
    try:
        text = payload.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PortableComputeReproductionError(f"{label} must be valid UTF-8 JSON") from exc
    counter = [0]
    _assert_bounded_json(value, label=label, depth=0, counter=counter)
    if type(value) is not dict:
        raise PortableComputeReproductionError(f"{label} must be plain object")
    return cast(dict[str, object], value)


def _assert_bounded_json(
    value: object,
    *,
    label: str,
    depth: int,
    counter: list[int],
) -> None:
    if depth > MAX_REPRODUCTION_MANIFEST_DEPTH:
        raise PortableComputeReproductionError(f"{label} exceeds depth limit")
    counter[0] += 1
    if counter[0] > MAX_REPRODUCTION_MANIFEST_ITEMS:
        raise PortableComputeReproductionError(f"{label} exceeds item limit")
    if type(value) is dict:
        for key, child in cast(dict[object, object], value).items():
            if type(key) is not str:
                raise PortableComputeReproductionError(f"{label} key must be text")
            _assert_bounded_json(
                child,
                label=label,
                depth=depth + 1,
                counter=counter,
            )
        return
    if type(value) is list:
        for child in cast(list[object], value):
            _assert_bounded_json(
                child,
                label=label,
                depth=depth + 1,
                counter=counter,
            )
        return
    if type(value) is str:
        if len(value.encode("utf-8")) > MAX_REPRODUCTION_MANIFEST_STRING_BYTES:
            raise PortableComputeReproductionError(f"{label} string exceeds byte limit")
        return
    if type(value) is float and not math.isfinite(value):
        raise PortableComputeReproductionError(f"{label} non-finite number forbidden")
    if value is None or type(value) in {bool, int, float}:
        return
    raise PortableComputeReproductionError(f"{label} value type forbidden")


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PortableComputeReproductionError("reproduction JSON duplicate key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise PortableComputeReproductionError(f"reproduction JSON constant forbidden: {value}")


def _canonical_zip_info(member_name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(member_name, date_time=REPRODUCTION_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.extra = b""
    info.comment = b""
    return info


def _read_regular_bounded_file(path: Path, *, label: str, max_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise PortableComputeReproductionError(f"{label} must be regular non-symlink file")
    size = path.stat().st_size
    if size > max_bytes:
        raise PortableComputeReproductionError(f"{label} exceeds byte limit")
    content = path.read_bytes()
    if len(content) != size or len(content) > max_bytes:
        raise PortableComputeReproductionError(f"{label} size drift")
    return content


def _resolve_regular_file(path: str | Path, label: str) -> Path:
    candidate = Path(path)
    if candidate.is_symlink():
        raise PortableComputeReproductionError(f"{label} must not be symlink")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_file() or resolved.is_symlink():
        raise PortableComputeReproductionError(f"{label} must be regular file")
    return resolved


def _resolve_directory(path: str | Path, label: str) -> Path:
    candidate = Path(path)
    if candidate.is_symlink():
        raise PortableComputeReproductionError(f"{label} must not be symlink")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_dir() or resolved.is_symlink():
        raise PortableComputeReproductionError(f"{label} must be directory")
    return resolved


def _assert_digest(value: object, label: str) -> None:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise PortableComputeReproductionError(f"reproduction {label} invalid")


def _assert_string_list(value: object, label: str, *, expected_count: int) -> list[str]:
    if type(value) is not list or len(value) != expected_count:
        raise PortableComputeReproductionError(f"reproduction {label} drift")
    items = cast(list[object], value)
    if any(not isinstance(item, str) for item in items):
        raise PortableComputeReproductionError(f"reproduction {label} invalid")
    return cast(list[str], items)


def _dump_json(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _digest_bytes(payload: bytes) -> str:
    return f"sha256:{_sha256_bytes(payload)}"


def _sha256_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()


__all__ = [
    "PORTABLE_COMPUTE_REPRODUCTION_CLI_NAME",
    "PORTABLE_COMPUTE_REPRODUCTION_CONTRACT",
    "PORTABLE_COMPUTE_REPRODUCTION_KIT_CONTRACT",
    "PORTABLE_COMPUTE_REPRODUCTION_KIT_SCHEMA_VERSION",
    "PORTABLE_COMPUTE_REPRODUCTION_PUBLIC_API_VERSION",
    "PORTABLE_COMPUTE_REPRODUCTION_RECEIPT_SCHEMA_VERSION",
    "PortableComputeReproductionError",
    "assert_portable_compute_reproduction_receipt",
    "build_portable_compute_reproduction_kit",
    "dump_portable_compute_reproduction_receipt",
    "emit_portable_compute_reproduction_receipt",
    "main",
    "reproduce_portable_compute",
]


if __name__ == "__main__":
    raise SystemExit(main())
