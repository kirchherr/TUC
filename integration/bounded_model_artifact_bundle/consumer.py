"""Deterministic installed-style bundle consumer; emits no generated source."""

from __future__ import annotations

import json
from hashlib import sha256

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_model_artifact_bundle import (
    MODEL_ARTIFACT_BUNDLE_CONTRACT,
    create_bounded_model_artifact_bundle,
    validate_bounded_model_artifact_bundle,
)
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind

SCHEMA_VERSION = "tuc.bounded_model_artifact_bundle_integration.v0"
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
    """Create and validate portable bundles under three capability sets."""

    cpu = _binding("cpu", DAGTarget.C11, _OPS)
    cuda = _binding("cuda", DAGTarget.CUDA_SM86, _OPS)
    mixed_cuda = _binding(
        "cuda",
        DAGTarget.CUDA_SM86,
        frozenset({OperationKind.MATMUL}),
        frozenset({OperationKind.MATMUL}),
    )
    base_model = _model(2.0)
    changed_model = _model(4.0)
    plans = []
    for name, bindings in (
        ("cpu", (cpu,)),
        ("cuda", (cuda,)),
        ("mixed", (cpu, mixed_cuda)),
    ):
        data = create_bounded_model_artifact_bundle(base_model, bindings)
        changed_data = create_bounded_model_artifact_bundle(changed_model, bindings)
        bundle = validate_bounded_model_artifact_bundle(base_model, bindings, data)
        changed = validate_bounded_model_artifact_bundle(changed_model, bindings, changed_data)
        artifact_sha256 = {item.name: item.sha256 for item in bundle.artifacts}
        assert artifact_sha256 == {item.name: item.sha256 for item in changed.artifacts}
        plans.append(
            {
                "artifact_sha256": artifact_sha256,
                "backend_bindings_digest": bundle.backend_bindings_digest,
                "bundle_bytes": len(data),
                "bundle_digest": bundle.bundle_digest,
                "changed_bundle_digest": changed.bundle_digest,
                "changed_model_compilation_digest": changed.model_compilation_digest,
                "decision_report_sha256": sha256(
                    bundle.decision_report.encode("utf-8")
                ).hexdigest(),
                "model_compilation_digest": bundle.model_compilation_digest,
                "name": name,
                "parameters": [item.tensor_name for item in bundle.parameter_bindings],
                "public_outputs": [item.public_name for item in bundle.output_bindings],
                "variable_inputs": [item.tensor_name for item in bundle.variable_input_bindings],
            }
        )
    return {
        "bundle_contract": MODEL_ARTIFACT_BUNDLE_CONTRACT,
        "device_access": False,
        "filesystem_access": False,
        "generated_code_execution": False,
        "native_compilation": False,
        "native_execution": False,
        "network_access": False,
        "plans": plans,
        "plugin_discovery": False,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "subprocess_execution": False,
    }


def main() -> int:
    print(_json(report()).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
