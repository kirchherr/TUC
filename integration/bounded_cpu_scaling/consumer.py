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
FAMILIES = ("scaler", "classifier", "attention")
SCHEMA = "tuc.bounded_cpu_scaling_integration.v0"
SIGNATURE_SCHEMA = "tuc.bounded_cpu_source.v0"
CLI_SCHEMA = "tuc.bounded_cpu_cli.v0"
INPUT_SCHEMA = "tuc.bounded_cpu_inputs.v0"
BATCH_SCHEMA = "tuc.bounded_cpu_batch.v0"
BATCH_CLI_SCHEMA = "tuc.bounded_cpu_batch_cli.v0"
RTOL, ATOL, MASS_ATOL = 2e-5, 2e-6, 8e-6
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
        raise ValueError("unknown fixed scaling graph")
    mul, add = {"elementwise_kind": "mul"}, {"elementwise_kind": "add"}
    if family == "scaler":
        shape = ((5,), (2, 3))[profile]
        tensors = (("x", shape), ("scale", (1,)), ("y", shape))
        operations = (("y", "elementwise", ["x", "scale"], mul),)
    elif family == "classifier":
        m, k, n = ((2, 3, 4), (1, 2, 3))[profile]
        tensors = (("x", (m, k)), ("gain", (k,)), ("scaled", (m, k)),
                   ("offset", (k,)), ("calibrated", (m, k)), ("weight", (n, k)),
                   ("p", (m, n)), ("bias", (n,)), ("logits", (m, n)), ("y", (m, n)))
        operations = (("scaled", "elementwise", ["x", "gain"], mul),
                      ("calibrated", "elementwise", ["scaled", "offset"], add),
                      ("p", "matmul", ["calibrated", "weight"], {"rhs_transposed": True}),
                      ("logits", "elementwise", ["p", "bias"], add),
                      ("y", "softmax", ["logits"], {"axis": 1}))
    else:
        m, k, seq, d = ((2, 4, 3, 2), (1, 2, 4, 3))[profile]
        tensors = (("q", (m, k)), ("key", (seq, k)), ("logits", (m, seq)),
                   ("scale", (1,)), ("scaled", (m, seq)), ("probability", (m, seq)),
                   ("value", (seq, d)), ("y", (m, d)))
        operations = (("logits", "matmul", ["q", "key"], {"rhs_transposed": True}),
                      ("scaled", "elementwise", ["logits", "scale"], mul),
                      ("probability", "softmax", ["scaled"], {"axis": 1}),
                      ("y", "matmul", ["probability", "value"], {}))
    return {"schema_version": "source_intent.v0", "name": f"scaling_{family}_{profile}",
            "tensors": [{"name": name, "shape": list(shape), "dtype": "float32"}
                        for name, shape in tensors],
            "operations": [{"name": name, "family": kind, "inputs": inputs, "outputs": [name],
                            "hints": {}, **({"attributes": attributes} if attributes else {})}
                           for name, kind, inputs, attributes in operations],
            "returns": [{"public_name": "scores", "tensor_name": "y", "required": True}]}


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
    if type(case) is not int or case not in (0, 1, 2):
        raise ValueError("unknown fixed scaling data")
    inputs, _ = public_bindings(graph(family, profile))
    values = {binding["public_name"]: [
        f32(((index * 5 + slot * 3 + case * 2 + profile) % 13 - 6) / (8.0, 7.0, 5.0)[case])
        for index in range(math.prod(binding["shape"]))]
        for slot, binding in enumerate(inputs)}
    if family == "scaler":
        values["scale"] = [0.5 if case == 0 else -0.25]
        values["x"][0] = -0.0
    elif family == "attention":
        values["scale"] = [0.5 if profile == 0 else 0.75]
    else:
        values["gain"] = [0.5 + 0.25 * ((i + case) % 3) for i in range(len(values["gain"]))]
    return {"schema_version": INPUT_SCHEMA, "inputs": values}


def _multiply(left, right):
    product = f32(left * right)
    if left != 0.0 and right != 0.0 and product == 0.0:
        raise ValueError("oracle nonzero product rounded to zero")
    return product


def _linear(left, weight, rows, inner, columns):
    """Weight is physically row-major [columns, inner]; accumulation is ordered."""
    result = []
    for row in range(rows):
        for column in range(columns):
            accumulator = 0.0
            for index in range(inner):
                product = _multiply(left[row * inner + index], weight[column * inner + index])
                accumulator = f32(accumulator + product)
            result.append(accumulator)
    return result


def softmax(values, rows, columns):
    """Ordered FP32 model; math.exp rounds to FP32 but is not an expf identity claim."""
    result = []
    for row in range(rows):
        items = values[row * columns:(row + 1) * columns]
        maximum = items[0]
        for item in items[1:]:
            if item > maximum:
                maximum = item
        exponentials = []
        total = 0.0
        for item in items:
            shifted = f32(item - maximum)
            exponential = f32(math.exp(shifted))
            if exponential <= 0.0:
                raise ValueError("softmax exponential must be positive normal")
            exponentials.append(exponential)
            total = f32(total + exponential)
        for exponential in exponentials:
            probability = f32(exponential / total)
            if probability <= 0.0:
                raise ValueError("softmax quotient must be positive normal")
            result.append(probability)
    return result


def reference(family, profile, envelope):
    values = envelope["inputs"]
    if family == "scaler":
        result = [_multiply(value, values["scale"][0]) for value in values["x"]]
    elif family == "classifier":
        m, k, n = ((2, 3, 4), (1, 2, 3))[profile]
        scaled = [_multiply(value, values["gain"][i % k]) for i, value in enumerate(values["x"])]
        calibrated = [f32(value + values["offset"][i % k]) for i, value in enumerate(scaled)]
        projected = _linear(calibrated, values["weight"], m, k, n)
        logits = [f32(value + values["bias"][i % n]) for i, value in enumerate(projected)]
        result = softmax(logits, m, n)
    elif family == "attention":
        m, k, seq, d = ((2, 4, 3, 2), (1, 2, 4, 3))[profile]
        logits = _linear(values["q"], values["key"], m, k, seq)
        scaled = [_multiply(value, values["scale"][0]) for value in logits]
        probability = softmax(scaled, m, seq)
        transposed = [values["value"][row * d + column]
                      for column in range(d) for row in range(seq)]
        result = _linear(probability, transposed, m, seq, d)
    else:
        raise ValueError("unknown fixed oracle family")
    return {"scores": result}


def source(family, profile):
    declared = graph(family, profile)
    if family == "scaler":
        arguments = "x, scale, scores"
        body = "    y = x * scale\n"
    elif family == "classifier":
        arguments = "x, gain, offset, weight, bias, scores"
        body = ("    scaled = x * gain\n    calibrated = scaled + offset\n"
                "    p = tl.dot(calibrated, tl.trans(weight))\n"
                "    logits = p + bias\n    y = tl.softmax(logits, axis=1)\n")
    else:
        arguments = "q, key, scale, value, scores"
        body = ("    logits = tl.dot(q, tl.trans(key))\n    scaled = logits * scale\n"
                "    probability = tl.softmax(scaled, axis=1)\n"
                "    y = tl.dot(probability, value)\n")
    return ("import triton\nimport triton.language as tl\n\n@triton.jit\n"
            f"def {declared['name']}({arguments}):\n" + body +
            "    tl.store(scores, y)\n").encode("ascii")


def signature(family, profile):
    declared = graph(family, profile)
    inputs, outputs = public_bindings(declared)
    return {"schema_version": SIGNATURE_SCHEMA, "source_name": declared["name"],
            "kernel_name": declared["name"],
            "tensor_shapes": {item["public_name"]: item["shape"] for item in inputs + outputs}}


def batch_data():
    initial = input_envelope("classifier", 0, 0)["inputs"]
    shared = {name: initial[name] for name in ("gain", "offset", "weight", "bias")}
    requests = [{"id": f"sample_{case}", "inputs": {
        "x": input_envelope("classifier", 0, case)["inputs"]["x"]}} for case in range(3)]
    return {"schema_version": BATCH_SCHEMA, "shared_inputs": shared, "requests": requests}


def merged_input(batch, request):
    return {"schema_version": INPUT_SCHEMA,
            "inputs": {**batch["shared_inputs"], **request["inputs"]}}


def candidate():
    programs = []
    for family in FAMILIES:
        for profile in range(2):
            inputs, outputs = public_bindings(graph(family, profile))
            cases = []
            for case in range(2):
                data = input_envelope(family, profile, case)
                cases.append({"case": case, "input_sha256": digest(encoded(data)),
                              "expected_outputs": reference(family, profile, data)})
            programs.append({"id": f"{family}_{profile}", "family": family, "profile": profile,
                             "source_sha256": digest(source(family, profile)),
                             "signature_sha256": digest(encoded(signature(family, profile))),
                             "inputs": inputs, "outputs": outputs, "cases": cases})
    batch = batch_data()
    batch_record = {"program_id": "classifier_0", "batch_sha256": digest(encoded(batch)),
                    "requests": [{"id": request["id"],
                                  "input_sha256": digest(encoded(merged_input(batch, request))),
                                  "expected_outputs": reference(
                                      "classifier", 0, merged_input(batch, request))}
                                 for request in batch["requests"]]}
    scalars = sum(len(case["expected_outputs"]["scores"])
                  for program in programs for case in program["cases"])
    scalars += sum(len(case["expected_outputs"]["scores"]) for case in batch_record["requests"])
    if scalars != 82:
        raise ValueError("fixed scaling corpus coverage changed")
    return {"schema_version": SCHEMA, "status": "PASS", "native_execution_observed": False,
            "source_conversions": 0, "case_runs": 0, "batch_runs": 0, "batch_request_runs": 0,
            "scalar_checks": 0, "row_mass_checks": 0, "negative_controls": 0,
            "numeric_rejections": 0, "planned_source_conversions": 6, "planned_case_runs": 12,
            "planned_batch_runs": 1, "planned_batch_request_runs": 3, "planned_scalar_checks": 82,
            "planned_row_mass_checks": 12, "planned_negative_controls": 8,
            "planned_numeric_rejections": 4,
            "bitexact_scalar_checks": 0, "tolerance_scalar_checks": 0,
            "planned_bitexact_scalar_checks": 22, "planned_tolerance_scalar_checks": 60,
            "numeric_tolerance": {"rtol": RTOL, "atol": ATOL, "row_mass_atol": MASS_ATOL},
            "programs": programs, "batch": batch_record}


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
    path = directory / "classifier-batch.json"
    snapshots[path] = encoded(batch_data())
    with path.open("xb") as stream:
        stream.write(snapshots[path])
    return snapshots


def emit():
    report = candidate()
    parent = ROOT / "tmp"
    if parent.is_symlink():
        raise ValueError("fixture directory rejected")
    parent.mkdir(mode=0o700, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="scaling-fixtures-", dir=parent))
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


def _check_outputs(actual, expected, *, bitexact=False):
    if type(actual) is not dict or list(actual) != list(expected):
        raise ValueError("CLI public output binding changed")
    for name, values in expected.items():
        observed = actual[name]
        if (type(observed) is not list or len(observed) != len(values) or
                any(type(value) is not float or not math.isfinite(value) for value in observed)):
            raise ValueError("finite public FP32 outputs required")
        if bitexact:
            if observed != values or any(struct.pack("<f", value) != struct.pack("<f", target)
                                        for value, target in zip(observed, values, strict=True)):
                raise ValueError("independent scaling FP32 bit comparison failed")
        elif any(abs(value - target) > ATOL + RTOL * abs(target)
                 for value, target in zip(observed, values, strict=True)):
            raise ValueError("independent composed FP32 tolerance comparison failed")
    return sum(map(len, expected.values()))


def _check_row_mass(actual, family, profile):
    if family != "classifier":
        return 0  # Attention probabilities are internal; scaler values are not probabilities.
    rows, columns = ((2, 4), (1, 3))[profile]
    values = actual["scores"]
    if len(values) != rows * columns or any(
            type(value) is not float or not math.isfinite(value) or value <= 0.0
            for value in values):
        raise ValueError("softmax probabilities must be finite and positive")
    for row in range(rows):
        if abs(math.fsum(values[row * columns:(row + 1) * columns]) - 1.0) > MASS_ATOL:
            raise ValueError("softmax row mass changed")
    return rows


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
    original = source("scaler", 1)
    declared = signature("scaler", 1)
    cases = [
        {"id": "source_literal", "source": original.replace(b"x * scale", b"x * 0.5"),
         "signature": declared, "reason": "source_rejected"},
        {"id": "source_reversal", "source": original.replace(b"x * scale", b"scale * x"),
         "signature": declared, "reason": "source_rejected"},
        {"id": "source_column", "source": original,
         "signature": {**declared, "tensor_shapes": {"x": [2, 3], "scale": [2, 1],
                                                    "scores": [2, 3]}},
         "reason": "source_rejected"},
        {"id": "source_wrong_width", "source": original,
         "signature": {**declared, "tensor_shapes": {"x": [2, 3], "scale": [4],
                                                    "scores": [2, 3]}},
         "reason": "source_rejected"},
    ]
    for name in ("rank0", "reversal", "column", "wrong_width"):
        value = graph("scaler", 1)
        if name == "reversal":
            value["operations"][0]["inputs"].reverse()
        else:
            value["tensors"][1]["shape"] = {
                "rank0": [], "column": [2, 1], "wrong_width": [4]}[name]
        cases.append({"id": "json_" + name, "graph": value, "reason": "graph_json_rejected"})
    return cases


def _negative_controls(converter, cpu, directory, workspace, snapshots):
    results = []
    for case in negative_cases():
        if "source" in case:
            path = directory / f"negative-{case['id']}.py"
            signature_path = directory / f"negative-{case['id']}.json"
            payloads = {path: case["source"], signature_path: encoded(case["signature"])}
            command = (converter, (str(path), "--signature", str(signature_path),
                                   "--workspace", str(workspace)))
            diagnostic = "tuc-source-to-json"
            hashes = {"source_sha256": digest(case["source"]),
                      "signature_sha256": digest(payloads[signature_path])}
        else:
            path = directory / f"negative-{case['id']}.json"
            payloads = {path: encoded(case["graph"])}
            command = (cpu, ("inspect", str(path)))
            diagnostic = "tuc-cpu-app"
            hashes = {"graph_sha256": digest(payloads[path])}
        for path, payload in payloads.items():
            with path.open("xb") as stream:
                stream.write(payload)
            snapshots[path] = payload
        result = _invoke(*command)
        if result != (2, b"", f"{diagnostic}: {case['reason']}\n".encode("ascii")):
            raise ValueError("negative control contract failed: " + case["id"])
        _unchanged(snapshots, workspace)
        results.append({"id": case["id"], "reason": case["reason"], **hashes})
    return results


def numeric_cases():
    maximum = struct.unpack("<f", struct.pack("<I", 0x7f7fffff))[0]
    minimum = struct.unpack("<f", struct.pack("<I", 0x00800000))[0]
    small = struct.unpack("<f", struct.pack("<I", 0x0d800000))[0]
    return [{"id": name, "schema_version": INPUT_SCHEMA,
             "inputs": {"x": [value] + [0.0] * 4, "scale": [factor]}}
            for name, value, factor in (("product_overflow", maximum, 2.0),
                                        ("product_subnormal", minimum, 0.5),
                                        ("nonzero_product_to_zero", small, small))]


def numeric_batch():
    batch = batch_data()
    batch["shared_inputs"]["gain"][0] = 2.0
    maximum = struct.unpack("<f", struct.pack("<I", 0x7f7fffff))[0]
    batch["requests"][-1]["inputs"]["x"] = [maximum] + [0.0] * 5
    return batch


def _numeric_controls(executable, directory, workspace, snapshots, program):
    results = []
    for case in numeric_cases():
        data = {"schema_version": case["schema_version"], "inputs": case["inputs"]}
        raw = encoded(data)
        path = directory / f"numeric-{case['id']}.json"
        with path.open("xb") as stream:
            stream.write(raw)
        snapshots[path] = raw
        result = _invoke(executable, ("run", str(directory / program["id"] / "graph.json"),
                                     "--inputs", str(path), "--workspace", str(workspace)))
        if result != (1, b"", b"tuc-cpu-app: numeric_rejection\n"):
            raise ValueError("scaling numeric rejection failed: " + case["id"])
        _unchanged(snapshots, workspace)
        results.append({"id": case["id"], "reason": "numeric_rejection",
                        "program_digest": program["program_digest"], "input_sha256": digest(raw),
                        "request_digest": _request_digest(
                            program["program_digest"], program["inputs"], data)})
    return results


def _batch_digest(program, requests):
    value = {"schema_version": BATCH_SCHEMA, "program_digest": program,
             "requests": [{"id": item["id"], "request_digest": item["request_digest"]}
                          for item in requests]}
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                             allow_nan=False).encode("ascii"))


def _numeric_batch_control(executable, directory, workspace, snapshots, program):
    batch = numeric_batch()
    raw = encoded(batch)
    path = directory / "numeric-batch-last.json"
    with path.open("xb") as stream:
        stream.write(raw)
    snapshots[path] = raw
    result = _invoke(executable, ("run-batch", str(directory / program["id"] / "graph.json"),
                                 "--batch", str(path), "--workspace", str(workspace)))
    if result != (1, b"", b"tuc-cpu-app: numeric_rejection\n"):
        raise ValueError("last-request numeric batch rejection failed")
    _unchanged(snapshots, workspace)
    identities = [{"id": request["id"], "request_digest": _request_digest(
        program["program_digest"], program["inputs"], merged_input(batch, request))}
        for request in batch["requests"]]
    return {"id": "batch_last_product_overflow", "reason": "numeric_rejection",
            "action": "run-batch", "request_index": 2, "batch_sha256": digest(raw),
            "program_digest": program["program_digest"],
            "batch_digest": _batch_digest(program["program_digest"], identities),
            "requests": identities}


def _check_batch(result, program, record):
    code, output, error = result
    if code != 0 or error or len(output) > OUTPUT_LIMIT:
        raise ValueError("batch success contract rejected")
    # Reuse the strict duplicate/nonfinite JSON decoder, then check this batch envelope.
    def pairs(items):
        values = {}
        for key, item in items:
            if key in values:
                raise ValueError("duplicate batch response field")
            values[key] = item
        return values
    def constant(_):
        raise ValueError("nonfinite batch response")
    value = json.loads(output, object_pairs_hook=pairs, parse_constant=constant)
    if (type(value) is not dict or set(value) != {
            "schema_version", "action", "program_digest", "batch_digest", "results",
            "native_execution_observed"} or value["schema_version"] != BATCH_CLI_SCHEMA or
            value["action"] != "run-batch" or
            value["program_digest"] != program["program_digest"] or
            value["native_execution_observed"] is not True or
            not _is_digest(value["batch_digest"]) or type(value["results"]) is not list or
            len(value["results"]) != 3):
        raise ValueError("batch response envelope rejected")
    batch = batch_data()
    checked, scalars, rows = [], 0, 0
    for observed, request, expected in zip(
            value["results"], batch["requests"], record["requests"], strict=True):
        request_hash = _request_digest(program["program_digest"], program["inputs"],
                                       merged_input(batch, request))
        if (type(observed) is not dict or set(observed) != {"id", "request_digest", "outputs"} or
                observed["id"] != request["id"] or observed["id"] != expected["id"] or
                observed["request_digest"] != request_hash):
            raise ValueError("ordered batch identity rejected")
        scalars += _check_outputs(observed["outputs"], expected["expected_outputs"])
        rows += _check_row_mass(observed["outputs"], "classifier", 0)
        checked.append({**expected, "request_digest": request_hash, "outputs": observed["outputs"]})
    if _batch_digest(program["program_digest"], checked) != value["batch_digest"]:
        raise ValueError("batch digest rejected")
    return {**record, "program_digest": program["program_digest"],
            "batch_digest": value["batch_digest"], "requests": checked}, scalars, rows


def run():
    converter, cpu = _installed_cli("tuc-source-to-json"), _installed_cli("tuc-cpu-app")
    report = candidate()
    scalar_checks = case_runs = row_checks = 0
    with tempfile.TemporaryDirectory(prefix="tuc-scaling-consumer-") as temporary:
        directory = Path(temporary)
        workspace = directory / "workspace"
        workspace.mkdir(mode=0o700)
        snapshots = _write_fixtures(directory, report)
        for program in report["programs"]:
            folder = directory / program["id"]
            converted = _graph_result(_invoke(converter, (
                str(folder / "kernel.py"), "--signature", str(folder / "signature.json"),
                "--workspace", str(workspace))), graph(program["family"], program["profile"]))
            _unchanged(snapshots, workspace)
            path = folder / "graph.json"
            with path.open("xb") as stream:
                stream.write(converted)
            snapshots[path] = converted
            program["emitted_graph_sha256"] = digest(converted)
            inspected = _success(_invoke(cpu, ("inspect", str(path))), "inspect")
            _check_public_bindings(inspected, program)
            program["program_digest"] = inspected["program_digest"]
            _unchanged(snapshots, workspace)
            requests = set()
            for case in program["cases"]:
                actual = _success(_invoke(cpu, ("run", str(path), "--inputs",
                    str(folder / f"inputs-{case['case']}.json"), "--workspace",
                    str(workspace))), "run")
                data = input_envelope(program["family"], program["profile"], case["case"])
                expected_request = _request_digest(
                    program["program_digest"], program["inputs"], data)
                if (actual["program_digest"] != program["program_digest"] or
                        actual["request_digest"] != expected_request):
                    raise ValueError("program or request identity changed")
                requests.add(actual["request_digest"])
                scalar_checks += _check_outputs(actual["outputs"], case["expected_outputs"],
                                                bitexact=program["family"] == "scaler")
                row_checks += _check_row_mass(
                    actual["outputs"], program["family"], program["profile"])
                case.update(request_digest=actual["request_digest"], outputs=actual["outputs"])
                case_runs += 1
                _unchanged(snapshots, workspace)
            if len(requests) != 2:
                raise ValueError("changing input did not change request identity")
        program = next(item for item in report["programs"] if item["id"] == "classifier_0")
        path = directory / "classifier-batch.json"
        batch, scalars, rows = _check_batch(_invoke(cpu, (
            "run-batch", str(directory / "classifier_0/graph.json"), "--batch", str(path),
            "--workspace", str(workspace))), program, report["batch"])
        report["batch"] = batch
        scalar_checks += scalars
        row_checks += rows
        _unchanged(snapshots, workspace)
        controls = _negative_controls(converter, cpu, directory, workspace, snapshots)
        numeric_program = next(item for item in report["programs"] if item["id"] == "scaler_0")
        numeric = _numeric_controls(cpu, directory, workspace, snapshots, numeric_program)
        numeric.append(_numeric_batch_control(cpu, directory, workspace, snapshots, program))
    if (case_runs != 12 or scalar_checks != 82 or row_checks != 12 or len(controls) != 8 or
            len(numeric) != 4 or len({item["program_digest"] for item in report["programs"]}) != 6):
        raise ValueError("scaling conformance coverage incomplete")
    report.update(native_execution_observed=True, source_conversions=6, case_runs=case_runs,
                  batch_runs=1, batch_request_runs=3, scalar_checks=scalar_checks,
                  row_mass_checks=row_checks, negative_controls=len(controls),
                  numeric_rejections=len(numeric), bitexact_scalar_checks=22,
                  tolerance_scalar_checks=60,
                  control_results=controls,
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


