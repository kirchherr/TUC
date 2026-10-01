"""Deterministic installed-style consumer; emits digests, never generated source."""

from __future__ import annotations

import json
from hashlib import sha256

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_model_artifacts import (
    MODEL_ARTIFACT_CONTRACT,
    compile_bounded_model_artifacts,
    validate_bounded_model_artifacts,
)
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind

SCHEMA_VERSION = "tuc.bounded_model_artifacts_integration.v0"
_OPS = frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION})


def _json(value: object) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode("ascii")
        + b"\n"
    )


def _model(weight: float) -> bytes:
    return _json(
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
                    {
                        "name": "project",
                        "family": "matmul",
                        "inputs": ["x", "w"],
                        "outputs": ["p"],
                    },
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


def _binding(
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


def report() -> dict[str, object]:
    """Compile the same model under three explicit capability sets."""

    cpu = _binding("cpu", DAGTarget.C11, _OPS)
    cuda = _binding("cuda", DAGTarget.CUDA_SM86, _OPS)
    mixed_cuda = _binding(
        "cuda",
        DAGTarget.CUDA_SM86,
        frozenset({OperationKind.MATMUL}),
        frozenset({OperationKind.MATMUL}),
    )
    plans = []
    base_model = _model(2.0)
    changed_model = _model(4.0)
    source_digest = None
    for name, bindings in (
        ("cpu", (cpu,)),
        ("cuda", (cuda,)),
        ("mixed", (cpu, mixed_cuda)),
    ):
        compiled = compile_bounded_model_artifacts(base_model, bindings)
        changed = compile_bounded_model_artifacts(changed_model, bindings)
        validate_bounded_model_artifacts(base_model, bindings, compiled)
        validate_bounded_model_artifacts(changed_model, bindings, changed)
        assert compiled.source_compilation.artifacts == changed.source_compilation.artifacts
        current_source = compiled.source_compilation.source_intent_digest
        source_digest = current_source if source_digest is None else source_digest
        assert current_source == source_digest
        plans.append(
            {
                "artifact_sha256": {
                    artifact_name: sha256(text.encode("utf-8")).hexdigest()
                    for artifact_name, text in sorted(
                        compiled.source_compilation.artifacts.files().items()
                    )
                },
                "backend_sequence": [
                    item.backend_name
                    for item in compiled.source_compilation.compilation.partition_plan.assignments
                ],
                "backend_bindings_digest": compiled.source_compilation.backend_bindings_digest,
                "changed_model_compilation_digest": changed.model_compilation_digest,
                "model_compilation_digest": compiled.model_compilation_digest,
                "name": name,
                "parameters": [item.tensor_name for item in compiled.parameter_bindings],
                "public_outputs": [
                    item.public_name for item in compiled.source_compilation.output_bindings
                ],
                "variable_inputs": [item.tensor_name for item in compiled.variable_input_bindings],
            }
        )
    first = compile_bounded_model_artifacts(base_model, (cpu,))
    changed = compile_bounded_model_artifacts(changed_model, (cpu,))
    return {
        "artifact_contract": MODEL_ARTIFACT_CONTRACT,
        "changed_model_digest": changed.model_digest,
        "device_access": False,
        "generated_code_execution": False,
        "model_digest": first.model_digest,
        "native_compilation": False,
        "native_execution": False,
        "plans": plans,
        "plugin_discovery": False,
        "schema_version": SCHEMA_VERSION,
        "source_intent_digest": source_digest,
        "status": "PASS",
        "subprocess_execution": False,
    }


def main() -> int:
    print(_json(report()).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
