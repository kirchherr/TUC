"""Installed-style invocation consumer; emits identities, never source or values."""

from __future__ import annotations

import json

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import (
    MODEL_ARTIFACT_REQUEST_CONTRACT,
    BoundedBackendBinding,
    create_bounded_model_artifact_bundle,
    create_bounded_model_artifact_request,
    validate_bounded_model_artifact_request,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind

SCHEMA_VERSION = "tuc.bounded_model_artifact_request_integration.v0"


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
                "name": "portable_invocation",
                "tensors": [{"name": name, "shape": [2, 2]} for name in ("x", "w", "p", "y")],
                "operations": [
                    {"name": "project", "family": "matmul", "inputs": ["x", "w"], "outputs": ["p"]},
                    {
                        "name": "activate",
                        "family": "elementwise",
                        "inputs": ["p"],
                        "outputs": ["y"],
                        "attributes": {"elementwise_kind": "relu"},
                    },
                ],
                "returns": [{"public_name": "scores", "tensor_name": "y"}],
            },
            "parameters": {"w": [weight, -1.0, 1.0, 3.0]},
        }
    )


def report() -> dict[str, object]:
    """Bind two variable inputs under CPU, CUDA and mixed capability plans."""

    ops = frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE})
    cpu = BoundedBackendBinding(
        BackendCapability("cpu", ops, memory_domain=MemoryDomainKind.HOST_RAM), DAGTarget.C11
    )
    cuda = BoundedBackendBinding(
        BackendCapability("cuda", ops, memory_domain=MemoryDomainKind.UNKNOWN), DAGTarget.CUDA_SM86
    )
    mixed = BoundedBackendBinding(
        BackendCapability(
            "cuda",
            frozenset({OperationKind.MATMUL}),
            preferred_for=frozenset({OperationKind.MATMUL}),
            memory_domain=MemoryDomainKind.UNKNOWN,
        ),
        DAGTarget.CUDA_SM86,
    )
    model = _model(2.0)
    changed_model = _model(4.0)
    inputs = tuple(
        _json({"schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": v}})
        for v in ([1.0, -0.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0])
    )
    plans = []
    for name, bindings in (("cpu", (cpu,)), ("cuda", (cuda,)), ("mixed", (cpu, mixed))):
        bundle = create_bounded_model_artifact_bundle(model, bindings)
        requests = tuple(
            create_bounded_model_artifact_request(model, bindings, bundle, data) for data in inputs
        )
        values = tuple(
            validate_bounded_model_artifact_request(model, bindings, bundle, data, request)
            for data, request in zip(inputs, requests, strict=True)
        )
        changed_bundle = create_bounded_model_artifact_bundle(changed_model, bindings)
        changed_request = create_bounded_model_artifact_request(
            changed_model, bindings, changed_bundle, inputs[0]
        )
        changed = validate_bounded_model_artifact_request(
            changed_model, bindings, changed_bundle, inputs[0], changed_request
        )
        assert values[0].request_digest != values[1].request_digest
        assert values[0].bundle_digest == values[1].bundle_digest
        assert changed.bundle_digest != values[0].bundle_digest
        assert changed.request_digest not in {value.request_digest for value in values}
        plans.append(
            {
                "name": name,
                "bundle_digest": values[0].bundle_digest,
                "backend_bindings_digest": values[0].backend_bindings_digest,
                "model_digest": values[0].model_digest,
                "model_compilation_digest": values[0].model_compilation_digest,
                "request_digests": [value.request_digest for value in values],
                "request_bytes": [len(request) for request in requests],
                "changed_bundle_digest": changed.bundle_digest,
                "changed_request_digest": changed.request_digest,
                "input_names": [item.tensor_name for item in values[0].inputs],
                "input_elements": 8,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "request_contract": MODEL_ARTIFACT_REQUEST_CONTRACT,
        "status": "PASS",
        "plans": plans,
        "device_access": False,
        "filesystem_access": False,
        "generated_code_execution": False,
        "native_compilation": False,
        "native_execution": False,
        "network_access": False,
        "plugin_discovery": False,
        "subprocess_execution": False,
    }


def main() -> int:
    print(_json(report()).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
