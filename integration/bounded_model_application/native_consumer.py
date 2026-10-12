"""Fixed installed Linux observations; default mode never builds or executes."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

SCHEMA = "tuc.bounded_model_application_native.v0"


def encoded(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
        + b"\n"
    )


def fixture(weight: float) -> bytes:
    return encoded(
        {
            "schema_version": "tuc.bounded_cpu_model.v0",
            "graph": {
                "schema_version": "source_intent.v0",
                "name": "portable_native_observation",
                "tensors": [
                    {"name": n, "shape": s}
                    for n, s in (
                        ("x", [2, 2]),
                        ("w", [2, 2]),
                        ("p", [2, 2]),
                        ("y", [2, 2]),
                        ("r", [2]),
                    )
                ],
                "operations": [
                    {
                        "name": "projection",
                        "family": "matmul",
                        "inputs": ["x", "w"],
                        "outputs": ["p"],
                    },
                    {
                        "name": "activation",
                        "family": "elementwise",
                        "inputs": ["p"],
                        "outputs": ["y"],
                        "attributes": {"elementwise_kind": "relu"},
                    },
                    {
                        "name": "rows",
                        "family": "reduction",
                        "inputs": ["p"],
                        "outputs": ["r"],
                        "attributes": {"axis": 1},
                    },
                ],
                "returns": [
                    {"public_name": p, "tensor_name": t}
                    for p, t in (("rows", "r"), ("scores", "y"))
                ],
            },
            "parameters": {"w": [weight, -1.0, 1.0, 3.0]},
        }
    )


def input_bytes(values: tuple[float, ...]) -> bytes:
    return encoded({"schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": values}})


def candidate() -> dict[str, object]:
    return {
        "schema_version": SCHEMA,
        "status": "candidate",
        "native_execution_observed": False,
        "planned_successful_runs": 3,
        "planned_scalar_checks": 18,
        "planned_rejections": 4,
    }


def run(root: Path) -> dict[str, object]:
    from tuc.backends.base import BackendCapability
    from tuc.backends.bounded_dag import DAGTarget
    from tuc.compiler.bounded_model_application import BoundedModelApplicationError
    from tuc.compiler.bounded_model_artifact_bundle import create_bounded_model_artifact_bundle
    from tuc.compiler.bounded_model_artifact_request import create_bounded_model_artifact_request
    from tuc.compiler.bounded_source import BoundedBackendBinding
    from tuc.ir.memory import MemoryDomainKind
    from tuc.ir.model import OperationKind
    from tuc.runtime.bounded_c11_application import BoundedC11ApplicationRuntimeError
    from tuc.runtime.bounded_model_application import run_bounded_model_application

    workspace = root / "workspace"
    workspace.mkdir(mode=0o700)
    capabilities = (
        BoundedBackendBinding(
            BackendCapability(
                "cpu",
                frozenset(
                    {OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}
                ),
                memory_domain=MemoryDomainKind.HOST_RAM,
            ),
            DAGTarget.C11,
        ),
    )
    records = []
    for name, weight, values in (
        ("base", 2.0, (1.0, -0.0, 3.0, 4.0)),
        ("variable", 2.0, (-2.0, 1.0, 0.0, -0.0)),
        ("parameter", 4.0, (1.0, -0.0, 3.0, 4.0)),
    ):
        model, inputs = fixture(weight), input_bytes(values)
        bundle = create_bounded_model_artifact_bundle(model, capabilities)
        request = create_bounded_model_artifact_request(model, capabilities, bundle, inputs)
        result = run_bounded_model_application(
            model, capabilities, bundle, inputs, request, workspace=workspace
        )
        assert not list(workspace.iterdir())
        records.append(
            {
                "name": name,
                "request": json.loads(request),
                "receipt": json.loads(result.receipt_data),
            }
        )
    model, inputs = fixture(2.0), input_bytes((1.0, -0.0, 3.0, 4.0))
    bundle = create_bounded_model_artifact_bundle(model, capabilities)
    request = create_bounded_model_artifact_request(model, capabilities, bundle, inputs)
    rejections = []
    for name, bad_inputs, bad_request in (
        ("malformed_request", inputs, b"{}"),
        ("wrong_extent", input_bytes((1.0,)), request),
        (
            "fixed_override",
            encoded(
                {
                    "schema_version": "tuc.bounded_cpu_inputs.v0",
                    "inputs": {"x": [1.0] * 4, "w": [1.0] * 4},
                }
            ),
            request,
        ),
    ):
        try:
            run_bounded_model_application(
                model, capabilities, bundle, bad_inputs, bad_request, workspace=workspace
            )
        except BoundedModelApplicationError:
            rejections.append({"name": name, "reason": "model_application_rejected"})
        else:
            raise AssertionError("invalid model invocation accepted")
        assert not list(workspace.iterdir())
    maximum = struct.unpack("<f", bytes.fromhex("ffff7f7f"))[0]
    numeric_inputs = input_bytes((maximum, 0.0, 0.0, 0.0))
    numeric_request = create_bounded_model_artifact_request(
        model, capabilities, bundle, numeric_inputs
    )
    try:
        run_bounded_model_application(
            model, capabilities, bundle, numeric_inputs, numeric_request, workspace=workspace
        )
    except BoundedC11ApplicationRuntimeError as error:
        assert error.reason == "numeric_rejection"
        rejections.append({"name": "numeric_overflow", "reason": error.reason})
    else:
        raise AssertionError("overflow invocation accepted")
    assert not list(workspace.iterdir())
    report = {
        "schema_version": SCHEMA,
        "status": "PASS",
        "native_execution_observed": True,
        "successful_runs": len(records),
        "cases": records,
        "rejections": rejections,
        "workspaces_clean": True,
    }
    with (root / "record.json").open("xb") as stream:
        stream.write(encoded(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    print(encoded(run(Path.cwd()) if args.run else candidate()).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
