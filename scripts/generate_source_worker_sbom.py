"""Generate a deterministic CycloneDX SBOM for the OCI source worker."""

from __future__ import annotations

import argparse
import json
import re
import uuid
from hashlib import sha256
from pathlib import Path

CYCLONEDX_SPEC_VERSION = "1.6"
WORKER_NAME = "tuc-source-ingestion-worker"
WORKER_VERSION = "research-v0"
WORKER_PLATFORM = "linux/amd64"
_BASE_IMAGE_RE = re.compile(r"^FROM python:([^@]+)@sha256:([a-f0-9]{64})$")
_REQUIREMENT_RE = re.compile(
    r"^numpy==([0-9]+(?:\.[0-9]+){2}) --hash=sha256:([a-f0-9]{64})$"
)


def generate_source_worker_sbom(project_root: Path) -> dict[str, object]:
    """Return a deterministic, material-bound worker SBOM."""

    dockerfile = project_root / "docker/source-worker/Dockerfile"
    requirements = project_root / "requirements/source-worker.txt"
    worker_source = project_root / "src/tuc/frontend/_isolated_source_ingestion_worker.py"
    dockerfile_text = dockerfile.read_text(encoding="utf-8")
    requirements_text = requirements.read_text(encoding="utf-8").strip()
    base_match = next(
        (
            match
            for line in dockerfile_text.splitlines()
            if (match := _BASE_IMAGE_RE.fullmatch(line)) is not None
        ),
        None,
    )
    requirement_match = _REQUIREMENT_RE.fullmatch(requirements_text)
    if base_match is None or requirement_match is None:
        raise ValueError("source worker supply-chain pins rejected")

    base_tag, base_digest = base_match.groups()
    numpy_version, numpy_digest = requirement_match.groups()
    material_digests = {
        "dockerfile": _digest_file(dockerfile),
        "requirements": _digest_file(requirements),
        "worker_source": _digest_file(worker_source),
    }
    serial_material = json.dumps(material_digests, sort_keys=True, separators=(",", ":"))
    serial = uuid.uuid5(uuid.NAMESPACE_URL, f"tuc:{WORKER_NAME}:{serial_material}")
    worker_ref = f"pkg:oci/{WORKER_NAME}@{WORKER_VERSION}"
    python_ref = f"pkg:oci/python@sha256:{base_digest}"
    numpy_ref = f"pkg:pypi/numpy@{numpy_version}"
    return {
        "bomFormat": "CycloneDX",
        "specVersion": CYCLONEDX_SPEC_VERSION,
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "container",
                "bom-ref": worker_ref,
                "name": WORKER_NAME,
                "version": WORKER_VERSION,
                "purl": worker_ref,
                "properties": [
                    {"name": "tuc:platform", "value": WORKER_PLATFORM},
                    *(
                        {"name": f"tuc:material:{name}:sha256", "value": digest}
                        for name, digest in sorted(material_digests.items())
                    ),
                ],
            },
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "tuc-generate-source-worker-sbom",
                        "version": "0",
                    }
                ]
            },
        },
        "components": [
            {
                "type": "container",
                "bom-ref": python_ref,
                "name": "python",
                "version": base_tag,
                "purl": python_ref,
                "hashes": [{"alg": "SHA-256", "content": base_digest}],
                "scope": "required",
            },
            {
                "type": "library",
                "bom-ref": numpy_ref,
                "name": "numpy",
                "version": numpy_version,
                "purl": numpy_ref,
                "hashes": [{"alg": "SHA-256", "content": numpy_digest}],
                "scope": "required",
            },
        ],
        "dependencies": [
            {"ref": worker_ref, "dependsOn": [python_ref, numpy_ref]},
            {"ref": python_ref, "dependsOn": []},
            {"ref": numpy_ref, "dependsOn": []},
        ],
    }


def _digest_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/tuc-source-ingestion-worker.cdx.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = generate_source_worker_sbom(args.project_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
