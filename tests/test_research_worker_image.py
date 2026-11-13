"""Current image policy is separate from the retained v0 proof materials."""

from __future__ import annotations

import importlib.util
from hashlib import sha256
from pathlib import Path

import pytest

from tuc.runtime import bounded_cpu_source

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_research_source_worker_sbom.py"
SPEC = importlib.util.spec_from_file_location("research_worker_sbom", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)
IMAGE = (
    "python:3.12-slim-bookworm@sha256:"
    "0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4"
)


def test_active_runtime_and_candidate_share_assessed_amd64_image():
    recipe = (ROOT / "docker/research-source-worker/Dockerfile").read_text()
    assert "FROM " + IMAGE + "\n" in recipe
    assert bounded_cpu_source._PYTHON_IMAGE == IMAGE
    runtime_recipe = dict(bounded_cpu_source._fixed_files())["Dockerfile"].decode()
    assert "FROM --platform=linux/amd64 " + IMAGE + "\n" in runtime_recipe
    # Keep the installed conversion path copy-only and offline.
    assert "RUN " not in runtime_recipe and "pip" not in runtime_recipe
    workflow = (ROOT / ".github/workflows/research-release-candidate.yml").read_text()
    assert "--file docker/research-source-worker/Dockerfile" in workflow
    assert "scripts/generate_research_source_worker_sbom.py" in workflow
    policy = (ROOT / "docker/research-source-worker/Dockerfile.dockerignore").read_text()
    assert "!src/**" not in policy
    admitted = {
        line[1:]
        for line in policy.splitlines()
        if line.startswith("!src/") and line.endswith(".py")
    }
    assert admitted == {"src/tuc/frontend/" + name + ".py" for name in bounded_cpu_source._MODULES}
    assert (
        "image=moby/buildkit:v0.35.0@sha256:"
        "a521fc1fd903a46c611c733dd692548512232fba2e0386d6055846a903d05a71"
    ) in workflow


def test_current_sbom_binds_context_policy_and_keeps_historical_profile_distinct():
    first = GENERATOR.generate_research_source_worker_sbom(ROOT)
    assert first == GENERATOR.generate_research_source_worker_sbom(ROOT)
    component = first["metadata"]["component"]
    assert component["version"] == "research-0.2.0"
    properties = {p["name"]: p["value"] for p in component["properties"]}
    for name, relative in GENERATOR._FILES.items():
        data = (ROOT / relative).read_bytes()
        assert properties[f"tuc:material:{name}:sha256"] == sha256(data).hexdigest()
        assert properties[f"tuc:material:{name}:path"] == relative
    assert first["components"][0]["hashes"][0]["content"] == IMAGE.split("sha256:")[1]
    assert len(first["components"]) == 1
    assert first["dependencies"][0]["dependsOn"] == [first["components"][0]["bom-ref"]]


@pytest.fixture
def materials(tmp_path):
    for relative in GENERATOR._FILES.values():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    return tmp_path


@pytest.mark.parametrize(
    "drift", ["floating-base", "extra-stage", "hidden-stage", "invalid-digest"]
)
def test_sbom_rejects_unlisted_build_inputs(materials, drift):
    recipe = materials / "docker/research-source-worker/Dockerfile"
    if drift == "floating-base":
        recipe.write_text(recipe.read_text().replace(IMAGE, "python:3.12-slim-bookworm"))
    elif drift == "extra-stage":
        recipe.write_text(recipe.read_text() + "\nFROM alpine:latest\n")
    elif drift == "hidden-stage":
        recipe.write_text(recipe.read_text() + "\n  from\talpine:latest\n")
    else:
        recipe.write_text(recipe.read_text().replace(IMAGE, IMAGE[:-1] + "g"))
    with pytest.raises(ValueError, match="supply-chain pins rejected"):
        GENERATOR.generate_research_source_worker_sbom(materials)


def test_pr_image_check_has_no_attestation_or_publishing_authority():
    workflow = (ROOT / ".github/workflows/research-worker-image.yml").read_text()
    assert "permissions:\n  contents: read\n" in workflow
    assert "id-token:" not in workflow and "attestations:" not in workflow
    assert "pypi" not in workflow and "pull_request_target" not in workflow
    assert "buildkitd-flags: --cdi-disabled" in workflow
    assert (
        "image=moby/buildkit:v0.35.0@sha256:"
        "a521fc1fd903a46c611c733dd692548512232fba2e0386d6055846a903d05a71"
    ) in workflow
    assert 'report["config_digest"]' in workflow
    assert "--entrypoint=/usr/local/bin/python" in workflow
    assert 'find_spec("pip") is None' in workflow
    assert 'find_spec("ensurepip") is None' in workflow
    assert 'find_spec("numpy") is None' in workflow
    assert "context_canary_excluded" in workflow
    assert "--network=none" in workflow and "--read-only" in workflow
    assert "network_host_request_rejected" in workflow
    assert 'response["status"] == "accepted"' in workflow
