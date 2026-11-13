"""Describe current research-worker materials; retain the frozen v0 generator."""

from __future__ import annotations

import argparse
import json
import re
import uuid
from hashlib import sha256
from pathlib import Path

_BASE = re.compile(r"^FROM python:([^@\s]+)@sha256:([a-f0-9]{64})$", re.MULTILINE)
_NUMPY = re.compile(r"numpy==([0-9]+(?:\.[0-9]+){2}) --hash=sha256:([a-f0-9]{64})")
_FILES = {
    "dockerfile": "docker/research-source-worker/Dockerfile",
    "build_context_policy": "docker/research-source-worker/Dockerfile.dockerignore",
    "requirements": "requirements/source-worker.txt",
    "worker_source": "src/tuc/frontend/_isolated_source_ingestion_worker.py",
}


def generate_research_source_worker_sbom(project_root: Path) -> dict[str, object]:
    """Return deterministic CycloneDX metadata for this finite build profile."""
    files = {name: (project_root / path).read_bytes() for name, path in _FILES.items()}
    recipe = "\n".join(files["dockerfile"].decode("utf-8").splitlines())
    bases = _BASE.findall(recipe)
    from_lines = [
        line for line in recipe.splitlines() if re.match(r"FROM\s", line.lstrip(), re.IGNORECASE)
    ]
    requirement = _NUMPY.fullmatch(files["requirements"].decode("utf-8").strip())
    if len(bases) != 1 or len(from_lines) != 1 or requirement is None:
        raise ValueError("research worker supply-chain pins rejected")
    tag, base_digest = bases[0]
    numpy_version, numpy_digest = requirement.groups()
    digests = {name: sha256(data).hexdigest() for name, data in files.items()}
    material = json.dumps(digests, sort_keys=True, separators=(",", ":"))
    worker_ref = "pkg:oci/tuc-source-ingestion-worker@research-0.2.0"
    python_ref = f"pkg:oci/python@sha256:{base_digest}"
    numpy_ref = f"pkg:pypi/numpy@{numpy_version}"
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "serialNumber": "urn:uuid:"
        + str(uuid.uuid5(uuid.NAMESPACE_URL, "tuc:research-worker:" + material)),
        "metadata": {
            "component": {
                "type": "container",
                "bom-ref": worker_ref,
                "name": "tuc-source-ingestion-worker",
                "version": "research-0.2.0",
                "purl": worker_ref,
                "properties": [
                    {"name": "tuc:platform", "value": "linux/amd64"},
                    *(
                        {"name": f"tuc:material:{name}:sha256", "value": digest}
                        for name, digest in sorted(digests.items())
                    ),
                    *(
                        {"name": f"tuc:material:{name}:path", "value": path}
                        for name, path in sorted(_FILES.items())
                    ),
                ],
            },
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "tuc-generate-research-worker-sbom",
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
                "version": tag,
                "purl": python_ref,
                "scope": "required",
                "hashes": [{"alg": "SHA-256", "content": base_digest}],
            },
            {
                "type": "library",
                "bom-ref": numpy_ref,
                "name": "numpy",
                "version": numpy_version,
                "purl": numpy_ref,
                "scope": "required",
                "hashes": [{"alg": "SHA-256", "content": numpy_digest}],
            },
        ],
        "dependencies": [
            {"ref": worker_ref, "dependsOn": [python_ref, numpy_ref]},
            {"ref": python_ref, "dependsOn": []},
            {"ref": numpy_ref, "dependsOn": []},
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output", type=Path, default=Path("dist/tuc-source-ingestion-worker.cdx.json")
    )
    args = parser.parse_args()
    report = generate_research_source_worker_sbom(args.project_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
