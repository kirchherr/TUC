"""Generate a minimal CycloneDX SBOM for TUC release artifacts."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
import uuid
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

CYCLONEDX_SPEC_VERSION = "1.6"


def _load_pyproject(project_root: Path) -> dict[str, Any]:
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.is_file():
        raise FileNotFoundError(f"missing pyproject.toml at {pyproject_path}")
    with pyproject_path.open("rb") as pyproject_file:
        return tomllib.load(pyproject_file)


def _requirement_name(requirement: str) -> str:
    try:
        from packaging.requirements import Requirement

        return Requirement(requirement).name
    except Exception:
        match = re.match(r"\s*([A-Za-z0-9_.-]+)", requirement)
        if match is None:
            raise ValueError(f"cannot parse requirement name: {requirement!r}") from None
        return match.group(1)


def _installed_version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def _purl(name: str, version: str | None = None) -> str:
    normalized_name = name.replace("_", "-").lower()
    if version:
        return f"pkg:pypi/{normalized_name}@{version}"
    return f"pkg:pypi/{normalized_name}"


def _external_references(urls: dict[str, str]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    mapping = {
        "Homepage": "website",
        "Repository": "vcs",
        "Issues": "issue-tracker",
    }
    for label, ref_type in mapping.items():
        url = urls.get(label)
        if url:
            refs.append({"type": ref_type, "url": url})
    return refs


def generate_sbom(project_root: Path) -> dict[str, Any]:
    pyproject = _load_pyproject(project_root)
    project = pyproject.get("project", {})
    project_name = str(project.get("name", "unknown"))
    project_version = str(project.get("version", "0.0.0"))
    project_ref = _purl(project_name, project_version)
    dependencies = [str(dependency) for dependency in project.get("dependencies", [])]
    urls = {str(key): str(value) for key, value in project.get("urls", {}).items()}

    components: list[dict[str, Any]] = []
    dependency_refs: list[str] = []
    for requirement in dependencies:
        dependency_name = _requirement_name(requirement)
        dependency_version = _installed_version(dependency_name)
        dependency_ref = _purl(dependency_name, dependency_version)
        component: dict[str, Any] = {
            "type": "library",
            "bom-ref": dependency_ref,
            "name": dependency_name,
            "purl": dependency_ref,
            "scope": "required",
        }
        if dependency_version:
            component["version"] = dependency_version
        components.append(component)
        dependency_refs.append(dependency_ref)

    root_component: dict[str, Any] = {
        "type": "application",
        "bom-ref": project_ref,
        "name": project_name,
        "version": project_version,
        "purl": project_ref,
        "licenses": [{"license": {"id": "Apache-2.0"}}],
    }
    external_refs = _external_references(urls)
    if external_refs:
        root_component["externalReferences"] = external_refs

    return {
        "bomFormat": "CycloneDX",
        "specVersion": CYCLONEDX_SPEC_VERSION,
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "tuc-generate-sbom",
                        "version": "0",
                    }
                ]
            },
            "component": root_component,
        },
        "components": components,
        "dependencies": [
            {
                "ref": project_ref,
                "dependsOn": dependency_refs,
            },
            *({"ref": dependency_ref, "dependsOn": []} for dependency_ref in dependency_refs),
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root containing pyproject.toml.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/tuc.cdx.json"),
        help="Output path for the CycloneDX JSON document.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    sbom = generate_sbom(args.project_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
