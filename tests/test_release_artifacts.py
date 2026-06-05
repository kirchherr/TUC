from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


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
