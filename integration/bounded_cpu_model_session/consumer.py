"""Installed Python-session consumer with fixed independent FP32 equations.

Default invocation is inert. --run opts into the unchanged isolated CPU runtime.
Only a completely successful run writes record.json in the client directory.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
from pathlib import Path

SCHEMA = "tuc.bounded_cpu_model_session_integration.v0"


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")


def fixture(softmax=False, changed=False):
    graph = {
        "schema_version": "source_intent.v0",
        "name": "session_classifier" if softmax else "session_linear",
        "tensors": [
            {"name": n, "shape": s}
            for n, s in (("x", [1, 2]), ("w", [2, 2]), ("b", [2]), ("p", [1, 2]), ("y", [1, 2]))
        ],
        "operations": [
            {
                "name": "linear",
                "family": "matmul",
                "inputs": ["x", "w"],
                "outputs": ["p"],
                "attributes": {"rhs_transposed": True},
            },
            {
                "name": "bias",
                "family": "elementwise",
                "inputs": ["p", "b"],
                "outputs": ["y"],
                "attributes": {"elementwise_kind": "add"},
            },
        ],
        "returns": [{"public_name": "scores", "tensor_name": "s" if softmax else "y"}],
    }
    if softmax:
        graph["tensors"].append({"name": "s", "shape": [1, 2]})
        graph["operations"].append(
            {
                "name": "probability",
                "family": "softmax",
                "inputs": ["y"],
                "outputs": ["s"],
                "attributes": {"axis": 1},
            }
        )
    return encoded(
        {
            "schema_version": "tuc.bounded_cpu_model.v0",
            "graph": graph,
            "parameters": {"w": [3 if changed else 2, -1, 1, 3], "b": [0.5, -0.0]},
        }
    )


def inputs(x, **extra):
    return encoded({"schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": x, **extra}})


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def reference(x, softmax=False, changed=False):
    scores = [
        f32(f32(f32(x[0] * (3 if changed else 2)) + f32(-x[1])) + 0.5),
        f32(f32(x[0]) + f32(3 * x[1])),
    ]
    if softmax:
        maximum = max(scores)
        exponentials = [f32(math.exp(f32(v - maximum))) for v in scores]
        total = f32(sum(exponentials))
        scores = [f32(v / total) for v in exponentials]
    return scores


def snapshot(workspace):
    children = list(workspace.iterdir())
    assert len(children) == 1 and children[0].is_dir()
    context = children[0]
    files = tuple(
        sorted(
            (str(p.relative_to(context)), hashlib.sha256(p.read_bytes()).hexdigest())
            for p in context.rglob("*")
            if p.is_file()
        )
    )
    assert files
    return context.name, context.stat().st_ino, files


def reject(operation, reason):
    try:
        operation()
    except ValueError as error:
        assert error.reason == reason
    else:
        raise AssertionError("expected rejection")


def run(root):
    from tuc.bounded_cpu_model_session import open_cpu_model

    workspace = root / "workspace"
    workspace.mkdir(mode=0o700)
    records = []
    controls = []
    identities = []
    reuse_checks = 0
    for family, softmax, changed, count in (
        ("linear", False, False, 16),
        ("classifier", True, False, 2),
        ("changed_parameters", False, True, 2),
    ):
        data = fixture(softmax, changed)
        with open_cpu_model(data, workspace=workspace) as session:
            assert not list(workspace.iterdir())  # open itself is inert
            reject(lambda: session.run(inputs([2, 3], b=[0.5, 0])), "model_json_rejected")
            controls.append(family + ":override")
            assert not list(workspace.iterdir())
            initial = None
            identities.append((session.program_digest, session.model_digest))
            for index in range(count):
                reject(lambda: session.run(inputs([1])), "model_json_rejected")
                x = [2, 3] if index % 2 == 0 else [-1, 2]
                result = session.run(inputs(x))
                assert result.sequence == index + 1
                assert result.program_digest == session.program_digest
                assert result.model_digest == session.model_digest
                assert len(result.request_digest) == 64
                assert len(result.outputs) == 1 and result.outputs[0][0] == "scores"
                actual, expected = result.outputs[0][1], reference(x, softmax, changed)
                assert len(actual) == len(expected) == 2
                for a, b in zip(actual, expected, strict=True):
                    assert math.isfinite(a)
                    if softmax:
                        assert abs(a - b) <= 2e-6 + 2e-5 * abs(b)
                    else:
                        assert struct.pack("<f", a) == struct.pack("<f", b)
                if softmax:
                    assert abs(sum(actual) - 1.0) <= 8e-6
                current = snapshot(workspace)
                if initial is None:
                    initial = current
                else:
                    assert current == initial
                    reuse_checks += 1
                records.append(
                    {
                        "family": family,
                        "sequence": result.sequence,
                        "model_digest": result.model_digest,
                        "program_digest": result.program_digest,
                        "request_digest": result.request_digest,
                        "inputs": x,
                        "expected": expected,
                        "outputs": actual,
                    }
                )
            if count == 16:
                reject(lambda: session.run(inputs([2, 3])), "session_limit")
                controls.append("request_limit")
        assert not list(workspace.iterdir())
        reject(lambda: session.run(inputs([2, 3])), "closed")
        controls.append(family + ":closed")
    assert identities[0][0] == identities[2][0] and identities[0][1] != identities[2][1]
    for index in range(2, 16):
        assert records[index]["request_digest"] == records[index % 2]["request_digest"]
    assert records[0]["request_digest"] != records[18]["request_digest"]
    with open_cpu_model(fixture(), workspace=workspace) as session:
        first = session.run(inputs([2, 3]))
        assert first.outputs == (("scores", (1.5, 11.0)),)
        reject(
            lambda: session.run(inputs([float.fromhex("0x1.fffffep+127"), 0])), "numeric_rejection"
        )
        assert not list(workspace.iterdir())
        reject(lambda: session.run(inputs([2, 3])), "closed")
        assert first.outputs == (("scores", (1.5, 11.0)),)
        controls.extend(("numeric_rejection", "closed_after_failure"))
    assert not list(workspace.iterdir())
    assert reuse_checks == 17 and len(records) == 20 and len(controls) == 9
    return {
        "schema_version": SCHEMA,
        "status": "PASS",
        "native_execution_observed": True,
        "sessions": 4,
        "successful_runs": 21,
        "scalar_checks": 42,
        "bitexact_scalar_checks": 38,
        "tolerance_scalar_checks": 4,
        "stable_context_checks": reuse_checks,
        "rejections": controls,
        "invalid_extent_rejections": 20,
        "workspaces_clean": True,
        "records": records,
        "before_numeric_failure": {
            "program_digest": first.program_digest,
            "model_digest": first.model_digest,
            "request_digest": first.request_digest,
            "outputs": first.outputs,
        },
    }


def main():
    if sys.argv[1:] == []:
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA,
                    "native_execution_observed": False,
                    "planned_sessions": 4,
                    "planned_successful_runs": 21,
                }
            )
        )
        return
    if sys.argv[1:] != ["--run"]:
        raise SystemExit("expected --run")
    root = Path(__file__).resolve().parent
    record = run(root)
    with (root / "record.json").open("xb") as output:
        output.write(encoded(record) + b"\n")
    print(json.dumps({"status": record["status"], "successful_runs": record["successful_runs"]}))


if __name__ == "__main__":
    main()
