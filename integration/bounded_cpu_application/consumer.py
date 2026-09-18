"""Installed application example and explicit CPU integration test.

Default mode prepares inert artifacts. --run explicitly builds and executes;
--emit-fuzz writes fixed native parser-test contexts without executing them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import tempfile
from pathlib import Path

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_c11_application import (
    encode_bounded_c11_inputs,
    prepare_bounded_c11_application,
)
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind

ROOT = Path(__file__).resolve().parent
GRAPHS = ("projection", "activation")


def bindings():
    return (BoundedBackendBinding(BackendCapability(
        "application_cpu", frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE,
                                      OperationKind.REDUCTION}),
        memory_domain=MemoryDomainKind.HOST_RAM), DAGTarget.C11),)


def module(graph):
    if graph == "activation":
        return SourceIntentModule("standalone_activation", (
            SourceIntentTensor("x", (2, 3)), SourceIntentTensor("y", (2, 3))), (
                SourceIntentOperation("activate", "elementwise", ("x",), ("y",),
                                      attributes={"elementwise_kind": "relu"}),),
            returns=(SourceIntentReturn("activated", "y"),))
    if graph != "projection":
        raise ValueError("unsupported example graph")
    return SourceIntentModule("projection_and_totals", tuple(
        SourceIntentTensor(name, shape) for name, shape in (
            ("a", (2, 3)), ("b", (3, 2)), ("p", (2, 2)), ("y", (2, 2)), ("s", (2,)))), (
                SourceIntentOperation("project", "matmul", ("a", "b"), ("p",)),
                SourceIntentOperation("activate", "elementwise", ("p",), ("y",),
                                      attributes={"elementwise_kind": "relu"}),
                SourceIntentOperation("summarize", "reduction", ("p",), ("s",),
                                      attributes={"axis": 1})),
        returns=(SourceIntentReturn("activated", "y"), SourceIntentReturn("totals", "s")))


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def inputs(graph, case):
    values = tuple(f32(((i * 7 + case * 3) % 17 - 8) / (7.0 if case == 1 else 8.0))
                   for i in range(6))
    if graph == "activation":
        return {"x": values}
    return {"a": values, "b": tuple(f32((i - case - 2) / 4.0) for i in range(6))}


def reference(graph, data):
    if graph == "activation":
        return {"activated": tuple(max(0.0, x) for x in data["x"])}
    result = []
    for row in range(2):
        for column in range(2):
            value = 0.0
            for inner in range(3):
                value = f32(value + f32(data["a"][row * 3 + inner] *
                                        data["b"][inner * 2 + column]))
            result.append(value)
    return {"activated": tuple(max(0.0, value) for value in result),
            "totals": tuple(f32(result[i] + result[i + 1]) for i in (0, 2))}


def candidate():
    return {"schema_version": "tuc.bounded_cpu_application_example.v0", "status": "PASS",
            "programs": {graph: prepare_bounded_c11_application(
                module(graph), bindings()).program_digest for graph in GRAPHS},
            "native_execution_observed": False}


def run():
    from tuc.runtime.bounded_c11_application import (
        BoundedC11ApplicationRuntimeError,
        build_bounded_c11_application,
    )

    result = candidate()
    examples, calls, scalars, numeric_rejections = {}, 0, 0, 0
    with tempfile.TemporaryDirectory(prefix="tuc-cpu-application-example-") as workspace:
        for graph in GRAPHS:
            with build_bounded_c11_application(
                    module(graph), bindings(), workspace=Path(workspace)) as application:
                examples[graph] = []
                for case in range(3):
                    data = inputs(graph, case)
                    expected = reference(graph, data)
                    for _ in range(2):
                        actual = application.run(data)
                        if list(actual) != list(expected) or actual != expected:
                            raise ValueError("independent numerical comparison failed")
                        calls += 1
                        scalars += sum(len(values) for values in actual.values())
                    examples[graph].append(actual)
                if graph == "projection":
                    bad = {"a": (f32(3.4028234663852886e38),) * 6, "b": (2.0,) * 6}
                    try:
                        application.run(bad)
                    except BoundedC11ApplicationRuntimeError as error:
                        if error.reason != "numeric_rejection":
                            raise
                        numeric_rejections += 1
                    else:
                        raise ValueError("numeric overflow was not rejected")
    if calls != 12 or scalars != 72 or numeric_rejections != 1:
        raise ValueError("application coverage incomplete")
    return {**result, "native_execution_observed": True, "case_runs": calls,
            "scalar_checks": scalars, "numeric_rejections": numeric_rejections,
            "results": examples}


def _array(name, value):
    return f"static const unsigned char {name}[{len(value)}] = {{" + ",".join(
        str(byte) for byte in value) + "};\n"


def emit_fuzz():
    parent = ROOT / "tmp"
    if parent.is_symlink():
        raise ValueError("example output parent rejected")
    parent.mkdir(exist_ok=True)
    for graph in GRAPHS:
        app = prepare_bounded_c11_application(module(graph), bindings())
        request = encode_bounded_c11_inputs(module(graph), bindings(), app, inputs(graph, 0))
        expected = reference(graph, inputs(graph, 0))
        payload = b"".join(struct.pack("<f", x) for values in expected.values() for x in values)
        response = b"TUCOUT01" + request[8:72] + b"\0" * 4 + payload
        directory = Path(tempfile.mkdtemp(prefix=f"application-{graph}-", dir=parent))
        files = app.files()
        files.update({name: (ROOT / name).read_text(encoding="utf-8") for name in (
            "fuzz.c", "fuzz.Dockerfile", "fuzz.Dockerfile.dockerignore")})
        files["seed.h"] = _array("seed", request) + _array("expected", response)
        for name, value in files.items():
            with (directory / name).open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(value)
        (directory / "request.bin").write_bytes(request)
        (directory / "expected.bin").write_bytes(response)
        (directory / "truncated.bin").write_bytes(request[:-1])
        (directory / "extra.bin").write_bytes(request + b"\0")
        (directory / "wrong-program.bin").write_bytes(request[:8] + bytes(32) + request[40:])
        # CI retention identifies the exact compiler program and test harness.
        identity = {"program_digest": app.program_digest,
                    "harness_digest": hashlib.sha256(files["fuzz.c"].encode()).hexdigest()}
        (directory / "identity.json").write_text(json.dumps(identity) + "\n", encoding="ascii")
        print(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--emit-fuzz", action="store_true")
    args = parser.parse_args()
    if args.emit_fuzz:
        emit_fuzz()
    else:
        print(json.dumps(run() if args.run else candidate(), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
