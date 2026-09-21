"""Standalone source-to-JSON-to-CPU conformance, with no TUC imports.

Default and --emit are inert. --run explicitly invokes the installed source
converter and CPU console beside this Python interpreter. Source stays data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import selectors
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FAMILIES = ("affine", "mlp", "mixed")
PROFILES = ((2, 3, 4), (1, 4, 2))
SCHEMA = "tuc.bounded_cpu_linear_integration.v0"
SIGNATURE_SCHEMA = "tuc.bounded_cpu_source.v0"
CLI_SCHEMA = "tuc.bounded_cpu_cli.v0"
INPUT_SCHEMA = "tuc.bounded_cpu_inputs.v0"
CALL_TIMEOUT = 700.0
OUTPUT_LIMIT = 2 * 1024 * 1024
ERROR_LIMIT = 4096


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("ascii")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def f32(value):
    result = struct.unpack("<f", struct.pack("<f", value))[0]
    bits = struct.unpack("<I", struct.pack("<f", result))[0] & 0x7fffffff
    exponent = bits & 0x7f800000
    if not math.isfinite(result) or (bits and not exponent):
        raise ValueError("oracle value is outside the checked FP32 domain")
    return result


def graph(family, profile):
    if family not in FAMILIES or type(profile) is not int or profile not in (0, 1):
        raise ValueError("unknown fixed Linear graph case")
    m, k, n = PROFILES[profile]
    h = (5, 3)[profile]
    if family == "affine":
        tensors = (("x", (m, k)), ("weight", (n, k)), ("p", (m, n)),
                   ("bias", (n,)), ("y", (m, n)))
        operations = (("p", "matmul", ["x", "weight"], {"rhs_transposed": True}),
                      ("y", "elementwise", ["p", "bias"], {"elementwise_kind": "add"}))
    elif family == "mlp":
        tensors = (("x", (m, k)), ("w1", (h, k)), ("p", (m, h)),
                   ("b1", (h,)), ("z", (m, h)), ("hidden", (m, h)),
                   ("w2", (n, h)), ("q", (m, n)), ("b2", (n,)), ("y", (m, n)))
        operations = (("p", "matmul", ["x", "w1"], {"rhs_transposed": True}),
                      ("z", "elementwise", ["p", "b1"], {"elementwise_kind": "add"}),
                      ("hidden", "elementwise", ["z"], {"elementwise_kind": "relu"}),
                      ("q", "matmul", ["hidden", "w2"], {"rhs_transposed": True}),
                      ("y", "elementwise", ["q", "b2"], {"elementwise_kind": "add"}))
    else:
        tensors = (("x", (m, k)), ("normal_weight", (k, h)), ("p", (m, h)),
                   ("linear_weight", (n, h)), ("y", (m, n)))
        operations = (("p", "matmul", ["x", "normal_weight"], {}),
                      ("y", "matmul", ["p", "linear_weight"], {"rhs_transposed": True}))
    return {
        "schema_version": "source_intent.v0", "name": f"linear_{family}_{profile}",
        "tensors": [{"name": name, "shape": list(shape), "dtype": "float32"}
                    for name, shape in tensors],
        "operations": [{"name": name, "family": kind, "inputs": inputs,
                        "outputs": [name], "hints": {},
                        **({"attributes": attributes} if attributes else {})}
                       for name, kind, inputs, attributes in operations],
        "returns": [{"public_name": "scores", "tensor_name": "y", "required": True}],
    }

def public_bindings(source):
    """Predict public identities from this client's declarations, not CLI output."""
    shapes = {tensor["name"]: tensor["shape"] for tensor in source["tensors"]}
    names, produced = [], set()
    for operation in source["operations"]:
        for name in operation["inputs"] + operation["outputs"]:
            if name not in names:
                names.append(name)
        produced.update(operation["outputs"])

    def binding(public, tensor):
        return {"public_name": public, "tensor_name": tensor,
                "tensor_index": names.index(tensor), "shape": shapes[tensor], "dtype": "float32"}

    return ([binding(name, name) for name in names if name not in produced],
            [binding(item["public_name"], item["tensor_name"]) for item in source["returns"]])


def input_envelope(family, profile, case):
    if type(case) is not int or case not in (0, 1):
        raise ValueError("unknown fixed data case")
    bindings, _ = public_bindings(graph(family, profile))
    values = {}
    for slot, binding in enumerate(bindings):
        denominator = 8.0 if case == 0 else 7.0
        values[binding["public_name"]] = [
            f32(((index * 7 + slot * 5 + case * 3 + profile) % 19 - 9) / denominator)
            for index in range(math.prod(binding["shape"]))]
    return {"schema_version": INPUT_SCHEMA, "inputs": values}


def _matmul(left, right, rows, inner, columns):
    result = []
    for row in range(rows):
        for column in range(columns):
            accumulator = 0.0
            for index in range(inner):
                product = f32(left[row * inner + index] * right[index * columns + column])
                accumulator = f32(accumulator + product)
            result.append(accumulator)
    return result


def _linear(left, weight, rows, inner, columns):
    """Weight is physically row-major [columns, inner]; no transpose is materialized."""
    result = []
    for row in range(rows):
        for column in range(columns):
            accumulator = 0.0
            for index in range(inner):
                product = f32(left[row * inner + index] * weight[column * inner + index])
                accumulator = f32(accumulator + product)
            result.append(accumulator)
    return result


def reference(family, profile, envelope):
    """Family arithmetic does not interpret emitted graph operations or bindings."""
    m, k, n = PROFILES[profile]
    values = envelope["inputs"]
    if family == "affine":
        projected = _linear(values["x"], values["weight"], m, k, n)
        return {"scores": [f32(value + values["bias"][index % n])
                           for index, value in enumerate(projected)]}
    if family == "mlp":
        h = (5, 3)[profile]
        projected = _linear(values["x"], values["w1"], m, k, h)
        biased = [f32(value + values["b1"][index % h])
                  for index, value in enumerate(projected)]
        hidden = [0.0 if value < 0.0 else value for value in biased]
        final = _linear(hidden, values["w2"], m, h, n)
        return {"scores": [f32(value + values["b2"][index % n])
                           for index, value in enumerate(final)]}
    if family == "mixed":
        h = (5, 3)[profile]
        projected = _matmul(values["x"], values["normal_weight"], m, k, h)
        return {"scores": _linear(projected, values["linear_weight"], m, h, n)}
    raise ValueError("unknown fixed Linear family")


def source(family, profile):
    name = f"linear_{family}_{profile}"
    if family == "affine":
        arguments = "x, weight, bias, scores"
        body = ("    p = tl.dot(x, tl.trans(weight))\n"
                "    y = p + bias\n"
                "    tl.store(scores, y)\n")
    elif family == "mlp":
        arguments = "x, w1, b1, w2, b2, scores"
        body = ("    p = tl.dot(x, tl.trans(w1))\n"
                "    z = p + b1\n"
                "    hidden = tl.where(z > 0.0, z, 0.0)\n"
                "    q = tl.dot(hidden, tl.trans(w2))\n"
                "    y = q + b2\n"
                "    tl.store(scores, y)\n")
    elif family == "mixed":
        arguments = "x, normal_weight, linear_weight, scores"
        body = ("    p = tl.dot(x, normal_weight)\n"
                "    y = tl.dot(p, tl.trans(linear_weight))\n"
                "    tl.store(scores, y)\n")
    else:
        raise ValueError("unknown fixed Linear source family")
    if type(profile) is not int or profile not in (0, 1):
        raise ValueError("unknown fixed Linear source profile")
    return ("import triton\nimport triton.language as tl\n\n@triton.jit\n"
            f"def {name}({arguments}):\n" + body).encode("ascii")

def signature(family, profile):
    expected = graph(family, profile)
    inputs, outputs = public_bindings(expected)
    return {"schema_version": SIGNATURE_SCHEMA, "source_name": expected["name"],
            "kernel_name": expected["name"],
            "tensor_shapes": {item["public_name"]: item["shape"] for item in inputs + outputs}}


def candidate():
    programs = []
    scalar_checks = 0
    for family in FAMILIES:
        for profile in range(len(PROFILES)):
            expected_graph = graph(family, profile)
            inputs, outputs = public_bindings(expected_graph)
            cases = []
            for case in range(2):
                data = input_envelope(family, profile, case)
                expected = reference(family, profile, data)
                scalar_checks += sum(map(len, expected.values()))
                cases.append({"case": case, "input_sha256": digest(encoded(data)),
                              "expected_outputs": expected})
            programs.append({"id": f"{family}_{profile}", "family": family, "profile": profile,
                             "source_sha256": digest(source(family, profile)),
                             "signature_sha256": digest(encoded(signature(family, profile))),
                             "inputs": inputs, "outputs": outputs, "cases": cases})
    if scalar_checks != 60:
        raise ValueError("fixed corpus coverage changed")
    return {"schema_version": SCHEMA, "status": "PASS", "native_execution_observed": False,
            "source_conversions": 0, "case_runs": 0, "scalar_checks": 0, "negative_controls": 0,
            "planned_source_conversions": 6, "planned_case_runs": 12,
            "planned_scalar_checks": scalar_checks, "planned_negative_controls": 10,
            "planned_numeric_rejections": 2, "numeric_rejections": 0,
            "programs": programs}


def _write_fixtures(directory, report):
    snapshots = {}
    for program in report["programs"]:
        family, profile = program["family"], program["profile"]
        folder = directory / program["id"]
        folder.mkdir(mode=0o700)
        files = {"kernel.py": source(family, profile),
                 "signature.json": encoded(signature(family, profile))}
        files.update({f"inputs-{case}.json": encoded(input_envelope(family, profile, case))
                      for case in range(2)})
        for name, value in files.items():
            path = folder / name
            with path.open("xb") as stream:
                stream.write(value)
            snapshots[path] = value
    return snapshots


def emit():
    report = candidate()
    parent = ROOT / "tmp"
    if parent.is_symlink():
        raise ValueError("fixture directory rejected")
    parent.mkdir(mode=0o700, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="linear-fixtures-", dir=parent))
    _write_fixtures(directory, report)
    report["fixture_directory"] = str(directory)
    (directory / "fixtures.json").write_bytes(encoded(report))
    return report


def _installed_cli(name):
    if name not in ("tuc-source-to-json", "tuc-cpu-app"):
        raise ValueError("unknown fixed console")
    if sys.platform != "linux":
        raise ValueError("explicit CLI execution requires Linux")
    executable = Path(sys.executable).absolute().parent / name
    metadata = executable.lstat()
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o022 or
            not os.access(executable, os.X_OK)):
        raise ValueError("installed console script rejected")
    return executable


def _invoke(executable, arguments):
    """Drain both fixed-command pipes within limits and terminate on timeout."""
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONNOUSERSITE"] = "1"
    process = subprocess.Popen((str(executable), *arguments), stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True, close_fds=True, env=environment)
    selector = None
    buffers = {"out": bytearray(), "err": bytearray()}
    deadline = time.monotonic() + CALL_TIMEOUT
    try:
        selector = selectors.DefaultSelector()
        for name, stream in (("out", process.stdout), ("err", process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("CLI deadline exceeded")
            for key, _ in selector.select(min(remaining, 0.1)):
                limit = OUTPUT_LIMIT if key.data == "out" else ERROR_LIMIT
                try:
                    chunk = os.read(key.fileobj.fileno(),
                                    min(65536, limit - len(buffers[key.data]) + 1))
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                elif len(buffers[key.data]) + len(chunk) > limit:
                    raise ValueError("CLI output budget exceeded")
                else:
                    buffers[key.data].extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError("CLI deadline exceeded")
        code = process.wait(timeout=remaining)
        return code, bytes(buffers["out"]), bytes(buffers["err"])
    except BaseException:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5.0)
        raise
    finally:
        if selector is not None:
            selector.close()
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()


def _success(result, action):
    code, output, error = result
    if code != 0 or error:
        raise ValueError("CLI success contract rejected")

    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate CLI response key")
            value[key] = item
        return value

    def constant(_):
        raise ValueError("nonfinite CLI response rejected")

    value = json.loads(output, object_pairs_hook=pairs, parse_constant=constant)
    keys = {"schema_version", "action", "program_digest", "native_execution_observed"}
    keys.update({"inputs", "outputs"} if action == "inspect" else {"request_digest", "outputs"})
    if (type(value) is not dict or set(value) != keys or value["schema_version"] != CLI_SCHEMA or
            value["action"] != action or value["native_execution_observed"] is not (action == "run")
            or not _is_digest(value["program_digest"])):
        raise ValueError("CLI response envelope rejected")
    if action == "run" and not _is_digest(value["request_digest"]):
        raise ValueError("CLI request identity rejected")
    return value


def _is_digest(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def _unchanged(snapshots, workspace):
    if any(path.read_bytes() != expected for path, expected in snapshots.items()):
        raise ValueError("CLI changed an original fixture")
    if any(workspace.iterdir()):
        raise ValueError("CLI left application resources in its workspace")


def _request_digest(program_digest, bindings, data):
    payload = b"".join(struct.pack("<f", number)
                       for binding in bindings for number in data["inputs"][binding["public_name"]])
    return digest(bytes.fromhex(program_digest) + payload)


def _check_outputs(actual, expected):
    if type(actual) is not dict or list(actual) != list(expected):
        raise ValueError("CLI public output binding changed")
    for name, values in expected.items():
        observed = actual[name]
        if (type(observed) is not list or len(observed) != len(values) or
                any(type(value) is not float or not math.isfinite(value) for value in observed) or
                observed != values or
                any(struct.pack("<f", actual) != struct.pack("<f", expected)
                    for actual, expected in zip(observed, values, strict=True))):
            raise ValueError("independent scalar FP32 comparison failed")
    return sum(map(len, expected.values()))


def _check_public_bindings(inspected, program):
    options = {"sort_keys": True, "separators": (",", ":"), "allow_nan": False}
    actual = [inspected["inputs"], inspected["outputs"]]
    expected = [program["inputs"], program["outputs"]]
    # Keep list order, and distinguish JSON booleans from integer indices/dimensions.
    if json.dumps(actual, **options) != json.dumps(expected, **options):
        raise ValueError("independent public binding comparison failed")


def _graph_result(result, expected):
    code, output, error = result
    if code != 0 or error or len(output) > 65536:
        raise ValueError("source converter success contract rejected")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate converted graph key")
            result[key] = value
        return result

    actual = json.loads(output, object_pairs_hook=pairs)
    # JSON encodings distinguish bool/int/float while ignoring object key order.
    options = {"sort_keys": True, "separators": (",", ":"), "allow_nan": False}
    if json.dumps(actual, **options) != json.dumps(expected, **options):
        raise ValueError("independent converted graph comparison failed")
    return output


def negative_cases():
    base = ("import triton\nimport triton.language as tl\n\n@triton.jit\n"
            "def rejected_linear(x, weight, result):\n"
            "    y = tl.dot(x, tl.trans(weight))\n    tl.store(result, y)\n").encode("ascii")

    def declared():
        return {"schema_version": SIGNATURE_SCHEMA, "source_name": "rejected_linear",
                "kernel_name": "rejected_linear",
                "tensor_shapes": {"x": [2, 3], "weight": [4, 3], "result": [2, 4]}}

    replacements = (
        ("arbitrary_call", b"tl.dot(x, tl.trans(arbitrary(weight)))"),
        ("double_transpose", b"tl.dot(x, tl.trans(tl.trans(weight)))"),
        ("lhs_transpose", b"tl.dot(tl.trans(x), weight)"),
        ("axes", b"tl.dot(x, tl.trans(weight, 1, 0))"),
        ("keyword_axes", b"tl.dot(x, tl.trans(weight, axes=(1, 0)))"),
        ("method", b"tl.dot(x, weight.trans())"),
        ("attribute", b"tl.dot(x, weight.T)"),
        ("nested_add", b"tl.dot(x, tl.trans(weight + weight))"),
    )
    cases = [{"id": name, "source": base.replace(b"tl.dot(x, tl.trans(weight))", expression),
              "signature": declared(), "reason": "source_rejected"}
             for name, expression in replacements]
    standalone = base.replace(b"    y = tl.dot(x, tl.trans(weight))",
                              b"    transposed = tl.trans(weight)\n"
                              b"    y = tl.dot(x, transposed)")
    cases.append({"id": "standalone", "source": standalone,
                  "signature": declared(), "reason": "source_rejected"})
    wrong_shape = declared()
    wrong_shape["tensor_shapes"]["weight"] = [4, 2]
    cases.append({"id": "shape_mismatch", "source": base,
                  "signature": wrong_shape, "reason": "source_rejected"})
    return cases

def _negative_controls(executable, directory, workspace, snapshots):
    results = []
    for case in negative_cases():
        source_path = directory / f"negative-{case['id']}.py"
        signature_path = directory / f"negative-{case['id']}.json"
        payloads = {source_path: case["source"], signature_path: encoded(case["signature"])}
        for path, payload in payloads.items():
            with path.open("xb") as stream:
                stream.write(payload)
            snapshots[path] = payload
        code, output, error = _invoke(executable, (
            str(source_path), "--signature", str(signature_path), "--workspace", str(workspace)))
        diagnostic = f"tuc-source-to-json: {case['reason']}\n".encode("ascii")
        if code != 2 or output or error != diagnostic:
            raise ValueError(f"source converter rejection contract failed: {case['id']}")
        _unchanged(snapshots, workspace)
        results.append({"id": case["id"], "reason": case["reason"],
                        "source_sha256": digest(case["source"]),
                        "signature_sha256": digest(payloads[signature_path])})
    return results


def numeric_cases():
    maximum = struct.unpack("<f", struct.pack("<I", 0x7f7fffff))[0]
    minimum = struct.unpack("<f", struct.pack("<I", 0x00800000))[0]
    return [
        {"id": "product_overflow", "schema_version": INPUT_SCHEMA,
         "inputs": {"x": [maximum] + [0.0] * 5,
                    "weight": [2.0] + [0.0] * 11, "bias": [0.0] * 4}},
        {"id": "product_subnormal", "schema_version": INPUT_SCHEMA,
         "inputs": {"x": [minimum] + [0.0] * 5,
                    "weight": [0.5] + [0.0] * 11, "bias": [0.0] * 4}},
    ]

def _numeric_controls(executable, directory, workspace, snapshots, program):
    results = []
    for case in numeric_cases():
        data = {"schema_version": case["schema_version"], "inputs": case["inputs"]}
        path = directory / f"numeric-{case['id']}.json"
        raw = encoded(data)
        with path.open("xb") as stream:
            stream.write(raw)
        snapshots[path] = raw
        code, output, error = _invoke(executable, (
            "run", str(directory / program["id"] / "graph.json"),
            "--inputs", str(path), "--workspace", str(workspace)))
        if code != 1 or output or error != b"tuc-cpu-app: numeric_rejection\n":
            raise ValueError(f"CPU numeric rejection contract failed: {case['id']}")
        _unchanged(snapshots, workspace)
        results.append({"id": case["id"], "reason": "numeric_rejection",
                        "program_digest": program["program_digest"], "input_sha256": digest(raw),
                        "request_digest": _request_digest(
                            program["program_digest"], program["inputs"], data)})
    return results


def run():
    converter, cpu = _installed_cli("tuc-source-to-json"), _installed_cli("tuc-cpu-app")
    report = candidate()
    conversions, scalar_checks, case_runs = 0, 0, 0
    with tempfile.TemporaryDirectory(prefix="tuc-linear-consumer-") as temporary:
        directory = Path(temporary)
        workspace = directory / "workspace"
        workspace.mkdir(mode=0o700)
        snapshots = _write_fixtures(directory, report)
        for program in report["programs"]:
            folder = directory / program["id"]
            source_path, signature_path = folder / "kernel.py", folder / "signature.json"
            conversion = _invoke(converter, (str(source_path), "--signature", str(signature_path),
                                            "--workspace", str(workspace)))
            converted = _graph_result(conversion, graph(program["family"], program["profile"]))
            _unchanged(snapshots, workspace)
            conversions += 1
            graph_path = folder / "graph.json"
            with graph_path.open("xb") as stream:
                stream.write(converted)
            snapshots[graph_path] = converted
            program["emitted_graph_sha256"] = digest(converted)
            inspected = _success(_invoke(cpu, ("inspect", str(graph_path))), "inspect")
            _check_public_bindings(inspected, program)
            program["program_digest"] = inspected["program_digest"]
            _unchanged(snapshots, workspace)
            requests = set()
            for case in program["cases"]:
                input_path = folder / f"inputs-{case['case']}.json"
                actual = _success(_invoke(cpu, (
                    "run", str(graph_path), "--inputs", str(input_path),
                    "--workspace", str(workspace))), "run")
                data = input_envelope(program["family"], program["profile"], case["case"])
                expected_request = _request_digest(
                    program["program_digest"], program["inputs"], data)
                if (actual["program_digest"] != program["program_digest"] or
                        actual["request_digest"] != expected_request):
                    raise ValueError("CLI program or request identity changed")
                requests.add(actual["request_digest"])
                scalar_checks += _check_outputs(actual["outputs"], case["expected_outputs"])
                case["request_digest"] = actual["request_digest"]
                case["outputs"] = actual["outputs"]
                case_runs += 1
                _unchanged(snapshots, workspace)
            if len(requests) != 2:
                raise ValueError("changing input did not change request identity")
        controls = _negative_controls(converter, directory, workspace, snapshots)
        numeric_program = next(item for item in report["programs"] if item["id"] == "affine_0")
        numeric = _numeric_controls(cpu, directory, workspace, snapshots, numeric_program)
    if (conversions != 6 or case_runs != 12 or scalar_checks != 60 or len(controls) != 10 or
            len({program["program_digest"] for program in report["programs"]}) != 6 or
            len(numeric) != 2):
        raise ValueError("source CLI execution coverage incomplete")
    report.update(native_execution_observed=True, source_conversions=conversions,
                  case_runs=case_runs, scalar_checks=scalar_checks, negative_controls=len(controls),
                  control_results=controls, numeric_rejections=len(numeric),
                  numeric_controls=numeric,
                  original_files_unchanged=True, workspaces_clean=True)
    with Path("record.json").open("xb") as stream:
        stream.write(encoded(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--emit", action="store_true")
    mode.add_argument("--run", action="store_true")
    arguments = parser.parse_args()
    report = run() if arguments.run else emit() if arguments.emit else candidate()
    sys.stdout.buffer.write(encoded(report))


if __name__ == "__main__":
    main()
