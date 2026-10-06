"""Portable bounded model artifact bundle tests."""

from __future__ import annotations

import ast
import json
from hashlib import sha256
from pathlib import Path

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import bounded_model_artifact_bundle as api
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind


def encode(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), allow_nan=False).encode()


def model(weight: float = 2.0) -> bytes:
    return encode(
        {
            "schema_version": "tuc.bounded_cpu_model.v0",
            "graph": {
                "schema_version": "source_intent.v0",
                "name": "portable_projection",
                "tensors": [
                    {"name": name, "shape": shape}
                    for name, shape in (
                        ("x", [2, 2]),
                        ("w", [2, 2]),
                        ("p", [2, 2]),
                        ("r", [2, 2]),
                        ("y", [2]),
                    )
                ],
                "operations": [
                    {"name": "project", "family": "matmul", "inputs": ["x", "w"], "outputs": ["p"]},
                    {
                        "name": "activate",
                        "family": "elementwise",
                        "inputs": ["p"],
                        "outputs": ["r"],
                        "attributes": {"elementwise_kind": "relu"},
                    },
                    {
                        "name": "summarize",
                        "family": "reduction",
                        "inputs": ["r"],
                        "outputs": ["y"],
                        "attributes": {"axis": 1},
                    },
                ],
                "returns": [{"public_name": "scores", "tensor_name": "y"}],
            },
            "parameters": {"w": [weight, -1.0, 1.0, 3.0]},
        }
    )


OPS = frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION})


def binding(
    name: str,
    target: DAGTarget,
    operations: frozenset[OperationKind],
    preferred: frozenset[OperationKind] = frozenset(),
) -> BoundedBackendBinding:
    return BoundedBackendBinding(
        BackendCapability(
            name,
            operations,
            preferred_for=preferred,
            memory_domain=(
                MemoryDomainKind.HOST_RAM if target is DAGTarget.C11 else MemoryDomainKind.UNKNOWN
            ),
        ),
        target,
    )


def cpu() -> BoundedBackendBinding:
    return binding("cpu", DAGTarget.C11, OPS)


def gpu() -> BoundedBackendBinding:
    return binding(
        "gpu",
        DAGTarget.CUDA_SM86,
        frozenset({OperationKind.MATMUL}),
        frozenset({OperationKind.MATMUL}),
    )


def test_bundle_is_deterministic_canonical_and_fully_bound() -> None:
    data = api.create_bounded_model_artifact_bundle(model(), (cpu(), gpu()))
    assert data == api.create_bounded_model_artifact_bundle(model(), (gpu(), cpu()))
    assert data.endswith(b"\n")
    value = api.inspect_bounded_model_artifact_bundle(data)
    validated = api.validate_bounded_model_artifact_bundle(model(), (cpu(), gpu()), data)
    assert validated == value
    assert len(value.bundle_digest) == len(value.model_digest) == 64
    assert value.source_intent_digest.startswith("sha256:")
    assert value.backend_bindings_digest.startswith("sha256:")
    assert tuple(item.tensor_name for item in value.parameter_bindings) == ("w",)
    assert value.parameter_bindings[0].value_bits == "00000040000080bf0000803f00004040"
    assert tuple(item.tensor_name for item in value.variable_input_bindings) == ("x",)
    assert tuple(item.public_name for item in value.output_bindings) == ("scores",)
    assert tuple(item.name for item in value.artifacts) == tuple(sorted(value.files()))
    assert set(value.files()) == {
        "generated.c",
        "generated.h",
        "kernels.cuh",
        "manifest.json",
        "schedule.h",
    }
    assert "preferred_for:matmul" in value.decision_report


def test_parameter_bits_change_only_model_bound_bundle_identity() -> None:
    first = api.inspect_bounded_model_artifact_bundle(
        api.create_bounded_model_artifact_bundle(model(), (cpu(), gpu()))
    )
    changed = api.inspect_bounded_model_artifact_bundle(
        api.create_bounded_model_artifact_bundle(model(4.0), (cpu(), gpu()))
    )
    assert first.files() == changed.files()
    assert first.source_intent_digest == changed.source_intent_digest
    assert first.model_digest != changed.model_digest
    assert first.model_compilation_digest != changed.model_compilation_digest
    assert first.bundle_digest != changed.bundle_digest
    assert first.parameter_bindings[0].value_bits != changed.parameter_bindings[0].value_bits


def test_capability_change_changes_bundle_and_artifact_context() -> None:
    mixed_data = api.create_bounded_model_artifact_bundle(model(), (cpu(), gpu()))
    cpu_data = api.create_bounded_model_artifact_bundle(model(), (cpu(),))
    mixed = api.inspect_bounded_model_artifact_bundle(mixed_data)
    cpu_only = api.inspect_bounded_model_artifact_bundle(cpu_data)
    assert mixed.model_digest == cpu_only.model_digest
    assert mixed.backend_bindings_digest != cpu_only.backend_bindings_digest
    assert mixed.model_compilation_digest != cpu_only.model_compilation_digest
    assert mixed.bundle_digest != cpu_only.bundle_digest
    with pytest.raises(api.BoundedModelArtifactBundleError):
        api.validate_bounded_model_artifact_bundle(model(), (cpu(),), mixed_data)


def test_file_mapping_is_fresh_and_hashes_cover_exact_text() -> None:
    value = api.inspect_bounded_model_artifact_bundle(
        api.create_bounded_model_artifact_bundle(model(), (cpu(),))
    )
    files = value.files()
    files["generated.c"] = "changed"
    assert value.files()["generated.c"] != "changed"
    for item in value.artifacts:
        assert item.sha256 == sha256(item.text.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    "data",
    (
        b"",
        b"{}",
        b"[]",
        b"NaN",
        b"\xff",
        bytearray(b"{}"),
        b'{"a":1,"a":2}',
    ),
)
def test_malformed_bundle_has_one_closed_diagnostic(data: object) -> None:
    with pytest.raises(
        api.BoundedModelArtifactBundleError, match="^model_artifact_bundle_rejected$"
    ):
        api.inspect_bounded_model_artifact_bundle(data)


def test_noncanonical_and_digest_or_source_drift_reject() -> None:
    data = api.create_bounded_model_artifact_bundle(model(), (cpu(), gpu()))
    document = json.loads(data)
    noncanonical = json.dumps(document, indent=2).encode()
    changed_digest = data.replace(document["bundle_digest"].encode(), b"0" * 64, 1)
    changed_source = data.replace(b"#include", b"#includf", 1)
    for damaged in (noncanonical, changed_digest, changed_source):
        with pytest.raises(api.BoundedModelArtifactBundleError):
            api.inspect_bounded_model_artifact_bundle(damaged)


def test_oversized_and_wrong_original_inputs_reject() -> None:
    data = api.create_bounded_model_artifact_bundle(model(), (cpu(),))
    with pytest.raises(api.BoundedModelArtifactBundleError):
        api.inspect_bounded_model_artifact_bundle(b" " * (api.MAX_MODEL_ARTIFACT_BUNDLE_BYTES + 1))
    with pytest.raises(api.BoundedModelArtifactBundleError):
        api.validate_bounded_model_artifact_bundle(model(4.0), (cpu(),), data)


def test_module_has_no_execution_or_filesystem_surface() -> None:
    source = Path(api.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(name.startswith("tuc.runtime") for name in imports)
    forbidden_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert forbidden_calls.isdisjoint({"compile", "eval", "exec", "open"})
    for forbidden in ("subprocess", "socket", "ctypes", "importlib", "pathlib"):
        assert forbidden not in source


@pytest.mark.parametrize(
    ("path", "marker"),
    (
        ("README.md", "portable model artifact bundles"),
        ("ROADMAP.md", "Portable Bounded Model Artifact Bundles"),
        ("TUC_MASTER_PLAN.md", "Portable bounded model artifact bundles"),
        ("docs/ROADMAP_STATUS.md", "Portable Bounded Model Artifact Bundles"),
        ("docs/BOUNDED_MODEL_ARTIFACT_BUNDLE.md", "# Transfer bounded model artifacts"),
        ("rfcs/0337-bounded-model-artifact-bundle.md", "# RFC 0337"),
    ),
)
def test_public_contract_is_bound_into_project_guidance(path: str, marker: str) -> None:
    assert marker in Path(path).read_text(encoding="utf-8")
