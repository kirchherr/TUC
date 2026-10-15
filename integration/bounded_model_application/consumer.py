"""Installed-style protocol bridge; synthetic responses are not native evidence."""

from __future__ import annotations

import json
import struct
from hashlib import sha256

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import (
    MODEL_APPLICATION_RESULT_CONTRACT,
    BoundedBackendBinding,
    BoundedModelApplicationError,
    create_bounded_model_artifact_bundle,
    create_bounded_model_artifact_request,
    decode_bounded_model_application_response,
    prepare_bounded_model_application,
    validate_bounded_model_application_result,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind

SCHEMA_VERSION = "tuc.bounded_model_application_integration.v0"


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
    """Demonstrate deterministic CPU admission and labelled synthetic responses."""
    ops = frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE})
    cpu = (
        BoundedBackendBinding(
            BackendCapability("cpu", ops, memory_domain=MemoryDomainKind.HOST_RAM), DAGTarget.C11
        ),
    )
    calls = []
    for name, weight, values in (
        ("base", 2.0, [1.0, -0.0, 3.0, 4.0]),
        ("variable", 2.0, [5.0, 6.0, 7.0, 8.0]),
        ("parameter", 4.0, [1.0, -0.0, 3.0, 4.0]),
    ):
        model = _model(weight)
        bundle = create_bounded_model_artifact_bundle(model, cpu)
        inputs = _json({"schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": values}})
        request = create_bounded_model_artifact_request(model, cpu, bundle, inputs)
        prepared = prepare_bounded_model_application(model, cpu, bundle, inputs, request)
        # This caller-created fixture deliberately provides no native execution evidence.
        response = (
            b"TUCOUT01" + prepared.request_frame[8:72] + struct.pack("<I4f", 0, 0.0, -0.0, 2.0, 3.0)
        )
        result = decode_bounded_model_application_response(
            model, cpu, bundle, inputs, request, response, 0
        )
        assert result == validate_bounded_model_application_result(
            model, cpu, bundle, inputs, request, response, 0, result.receipt_data
        )
        calls.append(
            {
                "name": name,
                "bundle_digest": prepared.bundle_digest,
                "request_digest": prepared.request_digest,
                "program_digest": prepared.application.program_digest,
                "protocol_request_digest": prepared.request_frame[40:72].hex(),
                "result_digest": result.result_digest,
                "receipt_sha256": sha256(result.receipt_data).hexdigest(),
                "request_frame_bytes": len(prepared.request_frame),
                "response_bytes": len(response),
                "outputs": [item.public_name for item in result.outputs],
            }
        )
    rejected = []
    for name, bindings in (
        (
            "cuda",
            (
                BoundedBackendBinding(
                    BackendCapability("cuda", ops, memory_domain=MemoryDomainKind.UNKNOWN),
                    DAGTarget.CUDA_SM86,
                ),
            ),
        ),
        (
            "mixed",
            (
                *cpu,
                BoundedBackendBinding(
                    BackendCapability(
                        "cuda",
                        frozenset({OperationKind.MATMUL}),
                        preferred_for=frozenset({OperationKind.MATMUL}),
                        memory_domain=MemoryDomainKind.UNKNOWN,
                    ),
                    DAGTarget.CUDA_SM86,
                ),
            ),
        ),
    ):
        model = _model(2.0)
        bundle = create_bounded_model_artifact_bundle(model, bindings)
        inputs = _json({"schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": [1.0] * 4}})
        request = create_bounded_model_artifact_request(model, bindings, bundle, inputs)
        try:
            prepare_bounded_model_application(model, bindings, bundle, inputs, request)
        except BoundedModelApplicationError:
            rejected.append(name)
        else:
            raise AssertionError("CPU application accepted non-CPU plan")
    return {
        "schema_version": SCHEMA_VERSION,
        "result_contract": MODEL_APPLICATION_RESULT_CONTRACT,
        "status": "PASS",
        "calls": calls,
        "rejected_targets": rejected,
        "synthetic_responses": True,
        "native_execution_observed": False,
        "filesystem_access": False,
        "network_access": False,
        "subprocess_execution": False,
        "native_compilation": False,
        "generated_code_execution": False,
        "plugin_discovery": False,
        "device_access": False,
    }


def main() -> int:
    print(_json(report()).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
