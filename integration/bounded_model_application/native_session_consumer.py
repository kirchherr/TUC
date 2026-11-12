"""Observe two bounded model sessions; default mode never imports TUC or executes."""

from __future__ import annotations

import argparse
import json
import struct
from hashlib import sha256
from pathlib import Path

SCHEMA = "tuc.bounded_model_application_session_observation.v0"


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
        "schema_version": SCHEMA, "status": "candidate",
        "native_execution_observed": False, "planned_sessions": 2,
        "planned_builds": 2, "planned_successful_runs": 3,
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
    from tuc.runtime import bounded_c11_application as runtime
    from tuc.runtime.bounded_model_application_session import (
        BoundedModelApplicationSessionError,
        open_bounded_model_application,
    )

    bindings = (
        BoundedBackendBinding(
            BackendCapability(
                "cpu",
                frozenset({
                    OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION,
                }),
                memory_domain=MemoryDomainKind.HOST_RAM,
            ),
            DAGTarget.C11,
        ),
    )
    workspace = root / "workspace"
    workspace.mkdir(mode=0o700)
    counts = {"build": 0, "run": 0}
    original_command = runtime._command

    def observed_command(context, arguments, **kwargs):
        if arguments[0] in counts:
            counts[arguments[0]] += 1
        return original_command(context, arguments, **kwargs)

    def context(weight, values):
        model = fixture(weight)
        inputs = input_bytes(values)
        bundle = create_bounded_model_artifact_bundle(model, bindings)
        request = create_bounded_model_artifact_request(model, bindings, bundle, inputs)
        return model, bindings, bundle, inputs, request

    cases, rejections, sequences = [], [], []
    base = context(2.0, (1.0, -0.0, 3.0, 4.0))
    variable = context(2.0, (-2.0, 1.0, 0.0, -0.0))
    parameter = context(4.0, (1.0, -0.0, 3.0, 4.0))
    runtime._command = observed_command
    try:
        first = open_bounded_model_application(*base[:3], workspace=workspace)
        assert not counts["build"] and not counts["run"] and not list(workspace.iterdir())
        with first:
            for name, ctx in (("base", base), ("variable", variable)):
                result = first.run(*ctx[3:])
                sequences.append(result.sequence)
                cases.append({
                    "name": name, "request": json.loads(ctx[4]),
                    "receipt": json.loads(result.result.receipt_data),
                })
            assert counts == {"build": 1, "run": 2}
            for name, bad_inputs, bad_request in (
                ("malformed_request", base[3], b"{}"),
                ("wrong_extent", input_bytes((1.0,)), base[4]),
                ("fixed_override", encoded({
                    "schema_version": "tuc.bounded_cpu_inputs.v0",
                    "inputs": {"x": [1.0] * 4, "w": [1.0] * 4},
                }), base[4]),
            ):
                try:
                    first.run(bad_inputs, bad_request)
                except BoundedModelApplicationError:
                    rejections.append({"name": name, "reason": "model_application_rejected"})
                else:
                    raise AssertionError("invalid session invocation accepted")
                assert counts == {"build": 1, "run": 2}
            maximum = struct.unpack("<f", bytes.fromhex("ffff7f7f"))[0]
            numeric = context(2.0, (maximum, 0.0, 0.0, 0.0))
            try:
                first.run(*numeric[3:])
            except BoundedModelApplicationSessionError as error:
                assert error.reason == "numeric_rejection"
                rejections.append({"name": "numeric_overflow", "reason": error.reason})
            else:
                raise AssertionError("numeric overflow accepted")
            assert counts == {"build": 1, "run": 3} and not list(workspace.iterdir())
            try:
                first.run(*base[3:])
            except BoundedModelApplicationSessionError as error:
                assert error.reason == "closed"
            else:
                raise AssertionError("failed session reused")
        with open_bounded_model_application(*parameter[:3], workspace=workspace) as second:
            result = second.run(*parameter[3:])
            sequences.append(result.sequence)
            cases.append({
                "name": "parameter", "request": json.loads(parameter[4]),
                "receipt": json.loads(result.result.receipt_data),
            })
        assert counts == {"build": 2, "run": 4} and sequences == [1, 2, 1]
        assert not list(workspace.iterdir())
    finally:
        runtime._command = original_command
    record = {
        "schema_version": "tuc.bounded_model_application_native.v0",
        "status": "PASS", "native_execution_observed": True,
        "successful_runs": len(cases), "cases": cases, "rejections": rejections,
        "workspaces_clean": True,
    }
    data = encoded(record)
    with (root / "record.json").open("xb") as stream:
        stream.write(data)
    report = {
        "schema_version": SCHEMA, "status": "PASS", "native_execution_observed": True,
        "sessions": 2, "docker_builds": counts["build"], "native_runs": counts["run"],
        "successful_runs": len(cases), "sequences": sequences,
        "closed_session_rejections": 1, "workspaces_clean": True,
        "record_sha256": sha256(data).hexdigest(),
    }
    with (root / "session-observation.json").open("xb") as stream:
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
