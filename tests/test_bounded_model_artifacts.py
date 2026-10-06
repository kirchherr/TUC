"""Capability-planned model artifacts and fail-closed boundary tests."""

from __future__ import annotations

import ast
import json
from dataclasses import fields, replace
from pathlib import Path

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import bounded_model_artifacts as api
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


def cpu() -> BoundedBackendBinding:
    return BoundedBackendBinding(
        BackendCapability(
            "cpu",
            frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}),
            memory_domain=MemoryDomainKind.HOST_RAM,
        ),
        DAGTarget.C11,
    )


def gpu() -> BoundedBackendBinding:
    return BoundedBackendBinding(
        BackendCapability(
            "gpu",
            frozenset({OperationKind.MATMUL}),
            preferred_for=frozenset({OperationKind.MATMUL}),
            memory_domain=MemoryDomainKind.UNKNOWN,
        ),
        DAGTarget.CUDA_SM86,
    )


def altered(value: object, **changes: object) -> object:
    result = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(result, field.name, changes.get(field.name, getattr(value, field.name)))
    return result


def test_model_parameters_and_variable_inputs_bind_to_capability_planned_artifacts() -> None:
    result = api.compile_bounded_model_artifacts(model(), (cpu(), gpu()))
    assert tuple(item.tensor_name for item in result.parameter_bindings) == ("w",)
    assert result.parameter_bindings[0].values == (2.0, -1.0, 1.0, 3.0)
    assert tuple(item.tensor_name for item in result.variable_input_bindings) == ("x",)
    assert tuple(item.public_name for item in result.source_compilation.output_bindings) == (
        "scores",
    )
    assert tuple(
        item.backend_name
        for item in result.source_compilation.compilation.partition_plan.assignments
    ) == ("gpu", "cpu", "cpu")
    assert len(result.model_digest) == len(result.model_compilation_digest) == 64
    assert result.source_compilation.artifacts.c11_source
    assert result.source_compilation.artifacts.cuda_source
    api.validate_bounded_model_artifacts(model(), (cpu(), gpu()), result)


def test_parameter_change_preserves_program_sources_but_changes_model_binding() -> None:
    first = api.compile_bounded_model_artifacts(model(), (cpu(), gpu()))
    changed = api.compile_bounded_model_artifacts(model(4.0), (cpu(), gpu()))
    assert first.source_compilation.artifacts == changed.source_compilation.artifacts
    assert (
        first.source_compilation.source_intent_digest
        == changed.source_compilation.source_intent_digest
    )
    assert first.model_digest != changed.model_digest
    assert first.model_compilation_digest != changed.model_compilation_digest


def test_capability_order_is_canonical_and_bound() -> None:
    left = api.compile_bounded_model_artifacts(model(), (cpu(), gpu()))
    right = api.compile_bounded_model_artifacts(model(), (gpu(), cpu()))
    assert left == right
    cpu_only = api.compile_bounded_model_artifacts(model(), (cpu(),))
    assert left.model_digest == cpu_only.model_digest
    assert left.model_compilation_digest != cpu_only.model_compilation_digest


@pytest.mark.parametrize(
    "field",
    ("model_digest", "model_compilation_digest", "parameter_bindings", "variable_input_bindings"),
)
def test_revalidation_rejects_wrapper_drift(field: str) -> None:
    result = api.compile_bounded_model_artifacts(model(), (cpu(), gpu()))
    bad = {
        "model_digest": "0" * 64,
        "model_compilation_digest": "0" * 64,
        "parameter_bindings": (),
        "variable_input_bindings": (),
    }[field]
    with pytest.raises(api.BoundedModelArtifactError, match="^model_artifact_rejected$"):
        api.validate_bounded_model_artifacts(
            model(), (cpu(), gpu()), altered(result, **{field: bad})
        )


def test_revalidation_rejects_nested_source_artifact_drift() -> None:
    result = api.compile_bounded_model_artifacts(model(), (cpu(), gpu()))
    artifacts = replace(result.source_compilation.artifacts, c11_source="changed")
    source = altered(result.source_compilation, artifacts=artifacts)
    with pytest.raises(api.BoundedModelArtifactError):
        api.validate_bounded_model_artifacts(
            model(), (cpu(), gpu()), altered(result, source_compilation=source)
        )


def test_revalidation_never_dispatches_methods_on_corrupted_wrapper_fields() -> None:
    class Hostile:
        def __eq__(self, other: object) -> bool:
            raise AssertionError("hostile comparison dispatched")

    result = api.compile_bounded_model_artifacts(model(), (cpu(), gpu()))
    parameter = altered(result.parameter_bindings[0], values=(Hostile(),))
    with pytest.raises(api.BoundedModelArtifactError):
        api.validate_bounded_model_artifacts(
            model(), (cpu(), gpu()), altered(result, parameter_bindings=(parameter,))
        )


@pytest.mark.parametrize("data", (b"", b"{}", b"[]", b"NaN", b"\xff", bytearray(b"{}")))
def test_hostile_model_input_has_one_closed_diagnostic(data: object) -> None:
    with pytest.raises(api.BoundedModelArtifactError, match="^model_artifact_rejected$"):
        api.compile_bounded_model_artifacts(data, (cpu(),))


def test_module_has_no_runtime_or_execution_surface() -> None:
    source = Path(api.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(name.startswith("tuc.runtime") for name in imports)
    for forbidden in ("subprocess", "socket", "ctypes", "importlib", "compile(", "exec(", "eval("):
        assert forbidden not in source


@pytest.mark.parametrize(
    ("path", "marker"),
    (
        ("README.md", "capability-planned model artifacts"),
        ("ROADMAP.md", "Capability-Planned Bounded Model Artifacts"),
        ("TUC_MASTER_PLAN.md", "Capability-planned bounded model artifacts"),
        ("docs/ROADMAP_STATUS.md", "Capability-Planned Bounded Model Artifacts"),
        ("docs/BOUNDED_MODEL_ARTIFACTS.md", "# Compile a bounded model"),
        ("rfcs/0336-bounded-model-artifacts.md", "# RFC 0336"),
    ),
)
def test_public_contract_is_bound_into_project_guidance(path: str, marker: str) -> None:
    assert marker in Path(path).read_text(encoding="utf-8")
