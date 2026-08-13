"""Verify a TUC source-worker OCI archive without extracting it."""

from __future__ import annotations

import argparse
import json
import re
import tarfile
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import IO, cast

MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_MEMBER_COUNT = 4096
MAX_JSON_BYTES = 1024 * 1024
EXPECTED_PLATFORM = {"architecture": "amd64", "os": "linux"}
EXPECTED_USER = "10001:10001"
EXPECTED_WORKING_DIR = "/run/tuc"
EXPECTED_ENTRYPOINT = [
    "python",
    "-I",
    "/opt/tuc/src/tuc/frontend/_isolated_source_ingestion_worker.py",
    "--oci",
]
OCI_MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
OCI_CONFIG_MEDIA_TYPE = "application/vnd.oci.image.config.v1+json"
OCI_LAYER_MEDIA_TYPES = frozenset(
    {
        "application/vnd.oci.image.layer.v1.tar",
        "application/vnd.oci.image.layer.v1.tar+gzip",
        "application/vnd.oci.image.layer.v1.tar+zstd",
    }
)
_DIGEST_RE = re.compile(r"^sha256:([a-f0-9]{64})$")


def verify_source_worker_oci_archive(archive_path: Path) -> dict[str, object]:
    """Validate OCI descriptors and the fixed worker runtime configuration."""

    archive_path = archive_path.resolve(strict=True)
    archive_size = archive_path.stat().st_size
    if archive_size <= 0 or archive_size > MAX_ARCHIVE_BYTES:
        raise ValueError("OCI archive size rejected")
    with tarfile.open(archive_path, mode="r:") as archive:
        members = archive.getmembers()
        if not members or len(members) > MAX_MEMBER_COUNT:
            raise ValueError("OCI archive member count rejected")
        member_map: dict[str, tarfile.TarInfo] = {}
        for member in members:
            normalized = _validated_member_name(member)
            if normalized in member_map:
                raise ValueError("OCI archive duplicate member rejected")
            member_map[normalized] = member

        layout = _read_json_member(archive, member_map, "oci-layout")
        if layout != {"imageLayoutVersion": "1.0.0"}:
            raise ValueError("OCI layout rejected")
        index = _read_json_member(archive, member_map, "index.json")
        manifests = index.get("manifests")
        if index.get("schemaVersion") != 2 or type(manifests) is not list:
            raise ValueError("OCI index rejected")
        if len(manifests) != 1 or type(manifests[0]) is not dict:
            raise ValueError("OCI manifest cardinality rejected")
        descriptor = cast(dict[str, object], manifests[0])
        if descriptor.get("mediaType") != OCI_MANIFEST_MEDIA_TYPE:
            raise ValueError("OCI manifest media type rejected")
        platform = descriptor.get("platform")
        if platform is not None and platform != EXPECTED_PLATFORM:
            raise ValueError("OCI platform descriptor rejected")
        manifest_digest, manifest = _read_descriptor_json(archive, member_map, descriptor)
        if (
            manifest.get("schemaVersion") != 2
            or manifest.get("mediaType") != OCI_MANIFEST_MEDIA_TYPE
        ):
            raise ValueError("OCI image manifest rejected")
        config_descriptor = manifest.get("config")
        layers = manifest.get("layers")
        if type(config_descriptor) is not dict or type(layers) is not list or not layers:
            raise ValueError("OCI image descriptors rejected")
        if config_descriptor.get("mediaType") != OCI_CONFIG_MEDIA_TYPE:
            raise ValueError("OCI config media type rejected")
        config_digest, config = _read_descriptor_json(
            archive,
            member_map,
            cast(dict[str, object], config_descriptor),
        )
        typed_layers = cast(list[object], layers)
        referenced_blob_digests = {manifest_digest, config_digest}
        for layer in typed_layers:
            if type(layer) is not dict:
                raise ValueError("OCI layer descriptor rejected")
            layer_descriptor = cast(dict[str, object], layer)
            if layer_descriptor.get("mediaType") not in OCI_LAYER_MEDIA_TYPES:
                raise ValueError("OCI layer media type rejected")
            referenced_blob_digests.add(
                _verify_descriptor_blob(archive, member_map, layer_descriptor)
            )
        _assert_worker_config(config)
        rootfs = cast(dict[str, object], config["rootfs"])
        diff_ids = cast(list[object], rootfs["diff_ids"])
        if len(diff_ids) != len(typed_layers):
            raise ValueError("OCI layer and rootfs cardinality rejected")
        _assert_exact_archive_members(member_map, referenced_blob_digests)

    return {
        "archive_digest": _digest_file(archive_path),
        "archive_size_bytes": archive_size,
        "config_digest": config_digest,
        "entrypoint": EXPECTED_ENTRYPOINT,
        "image_manifest_digest": manifest_digest,
        "layer_count": len(typed_layers),
        "platform": "linux/amd64",
        "rootfs_diff_id_count": len(diff_ids),
        "schema_version": "tuc.source_worker_oci_archive_verification.v0",
        "status": "PASS",
        "user": EXPECTED_USER,
        "working_dir": EXPECTED_WORKING_DIR,
    }


def _validated_member_name(member: tarfile.TarInfo) -> str:
    path = PurePosixPath(member.name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("OCI archive path rejected")
    if member.issym() or member.islnk() or member.isdev():
        raise ValueError("OCI archive special member rejected")
    if not (member.isfile() or member.isdir()):
        raise ValueError("OCI archive member type rejected")
    return str(path)


def _read_json_member(
    archive: tarfile.TarFile,
    members: dict[str, tarfile.TarInfo],
    name: str,
) -> dict[str, object]:
    member = members.get(name)
    if member is None or not member.isfile() or member.size > MAX_JSON_BYTES:
        raise ValueError("OCI JSON member rejected")
    extracted = archive.extractfile(member)
    if extracted is None:
        raise ValueError("OCI JSON member unavailable")
    return _decode_json(_read_bounded(extracted, member.size))


def _read_descriptor_json(
    archive: tarfile.TarFile,
    members: dict[str, tarfile.TarInfo],
    descriptor: dict[str, object],
) -> tuple[str, dict[str, object]]:
    digest, data = _read_descriptor_blob(archive, members, descriptor, MAX_JSON_BYTES)
    return digest, _decode_json(data)


def _verify_descriptor_blob(
    archive: tarfile.TarFile,
    members: dict[str, tarfile.TarInfo],
    descriptor: dict[str, object],
) -> str:
    digest, _data = _read_descriptor_blob(archive, members, descriptor, MAX_ARCHIVE_BYTES)
    return digest


def _assert_exact_archive_members(
    members: dict[str, tarfile.TarInfo],
    referenced_blob_digests: set[str],
) -> None:
    expected_files = {
        "index.json",
        "oci-layout",
        *(f"blobs/sha256/{digest.removeprefix('sha256:')}" for digest in referenced_blob_digests),
    }
    observed_files = {name for name, member in members.items() if member.isfile()}
    observed_directories = {name for name, member in members.items() if member.isdir()}
    if observed_files != expected_files:
        raise ValueError("OCI archive unreferenced member rejected")
    if not observed_directories.issubset({"blobs", "blobs/sha256"}):
        raise ValueError("OCI archive directory member rejected")


def _read_descriptor_blob(
    archive: tarfile.TarFile,
    members: dict[str, tarfile.TarInfo],
    descriptor: dict[str, object],
    max_bytes: int,
) -> tuple[str, bytes]:
    if set(descriptor) - {"annotations", "artifactType", "digest", "mediaType", "platform", "size"}:
        raise ValueError("OCI descriptor shape rejected")
    digest = descriptor.get("digest")
    size = descriptor.get("size")
    if not isinstance(digest, str) or not isinstance(size, int) or size < 0:
        raise ValueError("OCI descriptor fields rejected")
    match = _DIGEST_RE.fullmatch(digest)
    if match is None or size > max_bytes:
        raise ValueError("OCI descriptor bounds rejected")
    member = members.get(f"blobs/sha256/{match.group(1)}")
    if member is None or not member.isfile() or member.size != size:
        raise ValueError("OCI descriptor blob rejected")
    extracted = archive.extractfile(member)
    if extracted is None:
        raise ValueError("OCI descriptor blob unavailable")
    data = _read_bounded(extracted, size)
    if sha256(data).hexdigest() != match.group(1):
        raise ValueError("OCI descriptor digest rejected")
    return digest, data


def _read_bounded(source: IO[bytes], expected_size: int) -> bytes:
    data = source.read(expected_size + 1)
    if len(data) != expected_size:
        raise ValueError("OCI member size rejected")
    return data


def _decode_json(data: bytes) -> dict[str, object]:
    try:
        payload = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("OCI JSON rejected") from exc
    if type(payload) is not dict:
        raise ValueError("OCI JSON object rejected")
    return cast(dict[str, object], payload)


def _assert_worker_config(config: dict[str, object]) -> None:
    runtime = config.get("config")
    rootfs = config.get("rootfs")
    if type(runtime) is not dict or type(rootfs) is not dict:
        raise ValueError("OCI config shape rejected")
    runtime_map = cast(dict[str, object], runtime)
    rootfs_map = cast(dict[str, object], rootfs)
    if runtime_map.get("User") != EXPECTED_USER:
        raise ValueError("OCI worker user rejected")
    if runtime_map.get("WorkingDir") != EXPECTED_WORKING_DIR:
        raise ValueError("OCI worker working directory rejected")
    if runtime_map.get("Entrypoint") != EXPECTED_ENTRYPOINT:
        raise ValueError("OCI worker entrypoint rejected")
    if runtime_map.get("Cmd") not in (None, []):
        raise ValueError("OCI worker command override rejected")
    diff_ids = rootfs_map.get("diff_ids")
    if rootfs_map.get("type") != "layers" or type(diff_ids) is not list or not diff_ids:
        raise ValueError("OCI rootfs rejected")
    if not all(isinstance(value, str) and _DIGEST_RE.fullmatch(value) for value in diff_ids):
        raise ValueError("OCI rootfs digest rejected")


def _digest_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("dist/tuc-source-ingestion-worker.oci-verification.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = verify_source_worker_oci_archive(args.archive)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
