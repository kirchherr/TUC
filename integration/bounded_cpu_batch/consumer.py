"""Standalone installed CPU batch conformance; no TUC or repository imports.

Default and --emit are inert. --run explicitly invokes the installed CPU console
beside this Python interpreter. No resident-weight or performance claim is made.
"""

from __future__ import annotations

import argparse
import copy
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
FAMILIES = ("linear", "gated_mlp", "product")
SCHEMA = "tuc.bounded_cpu_batch_integration.v0"
BATCH_SCHEMA = "tuc.bounded_cpu_batch.v0"
OUTPUT_SCHEMA = "tuc.bounded_cpu_batch_cli.v0"
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
    magnitude = struct.unpack("<I", struct.pack("<f", result))[0] & 0x7fffffff
    if not math.isfinite(result) or (magnitude and not magnitude & 0x7f800000):
        raise ValueError("oracle value is outside the checked FP32 domain")
    return result


def graph(family, profile):
    if family not in FAMILIES or type(profile) is not int or profile not in (0, 1):
        raise ValueError("unknown fixed batch graph")
    linear, add = {"rhs_transposed": True}, {"elementwise_kind": "add"}
    if family == "linear":
        m, k, n = ((2, 3, 3), (1, 2, 2))[profile]
        tensors = (("x", (m, k)), ("weight", (n, k)), ("p", (m, n)),
                   ("bias", (n,)), ("y", (m, n)))
        operations = (("p", "matmul", ["x", "weight"], linear),
                      ("y", "elementwise", ["p", "bias"], add))
    elif family == "gated_mlp":
        m, k, h, n = ((2, 3, 4, 2), (1, 2, 3, 3))[profile]
        tensors = (("x", (m, k)), ("wv", (h, k)), ("v", (m, h)), ("bv", (h,)),
                   ("value", (m, h)), ("wg", (h, k)), ("g", (m, h)), ("bg", (h,)),
                   ("shifted", (m, h)), ("gate", (m, h)), ("fused", (m, h)),
                   ("wo", (n, h)), ("projected", (m, n)), ("bout", (n,)), ("y", (m, n)))
        operations = (("v", "matmul", ["x", "wv"], linear),
                      ("value", "elementwise", ["v", "bv"], add),
                      ("g", "matmul", ["x", "wg"], linear),
                      ("shifted", "elementwise", ["g", "bg"], add),
                      ("gate", "elementwise", ["shifted"], {"elementwise_kind": "relu"}),
                      ("fused", "elementwise", ["value", "gate"], {"elementwise_kind": "mul"}),
                      ("projected", "matmul", ["fused", "wo"], linear),
                      ("y", "elementwise", ["projected", "bout"], add))
    elif profile == 0:
        tensors = (("left", (5,)), ("right", (5,)), ("y", (5,)))
        operations = (("y", "elementwise", ["left", "right"], {"elementwise_kind": "mul"}),)
    else:
        tensors = (("x", (2, 3)), ("y", (2, 3)))
        operations = (("y", "elementwise", ["x", "x"], {"elementwise_kind": "mul"}),)
    return {"schema_version": "source_intent.v0", "name": f"batch_{family}_{profile}",
            "tensors": [{"name": name, "shape": list(shape), "dtype": "float32"}
                        for name, shape in tensors],
            "operations": [{"name": name, "family": kind, "inputs": inputs,
                            "outputs": [name], "hints": {}, "attributes": attributes}
                           for name, kind, inputs, attributes in operations],
            "returns": [{"public_name": "scores", "tensor_name": "y", "required": True}]}


def public_bindings(source):
    shapes = {tensor["name"]: tensor["shape"] for tensor in source["tensors"]}
    names, produced = [], set()
    for op in source["operations"]:
        for name in op["inputs"] + op["outputs"]:
            if name not in names:
                names.append(name)
        produced.update(op["outputs"])

    def binding(public, tensor):
        return {"public_name": public, "tensor_name": tensor, "tensor_index": names.index(tensor),
                "shape": shapes[tensor], "dtype": "float32"}

    return ([binding(name, name) for name in names if name not in produced],
            [binding(item["public_name"], item["tensor_name"]) for item in source["returns"]])


def batch_data(family, profile):
    bindings, _ = public_bindings(graph(family, profile))
    changing = "left" if family == "product" and profile == 0 else "x"
    shared, requests = {}, []
    for slot, binding in enumerate(bindings):
        name = binding["public_name"]
        if name != changing:
            shared[name] = [f32(((i * 5 + slot * 3 + profile) % 17 - 8) / 8.0)
                            for i in range(math.prod(binding["shape"]))]
    if family == "product" and profile == 0:
        shared["right"][0] = 2.0
    count = math.prod(next(binding["shape"] for binding in bindings
                           if binding["public_name"] == changing))
    for case in range(3):
        values = [f32(((i * 7 + case * 3 + profile) % 19 - 9) / (8.0, 7.0, 5.0)[case])
                  for i in range(count)]
        if family == "product" and case == 1:
            values[0] = -0.0
        requests.append({"id": f"sample_{case}", "inputs": {changing: values}})
    return {"schema_version": BATCH_SCHEMA, "shared_inputs": shared, "requests": requests}


def merged_input(batch, request):
    return {"schema_version": INPUT_SCHEMA,
            "inputs": {**batch.get("shared_inputs", {}), **request["inputs"]}}


def multiply(left, right):
    value = f32(left * right)
    if left != 0.0 and right != 0.0 and value == 0.0:
        raise ValueError("oracle nonzero product rounded to zero")
    return value


def linear(left, weight, m, k, n):
    result = []
    for row in range(m):
        for column in range(n):
            total = 0.0
            for index in range(k):
                total = f32(total + multiply(left[row * k + index], weight[column * k + index]))
            result.append(total)
    return result


def reference(family, profile, data):
    values = data["inputs"]
    if family == "product":
        left, right = ((values["left"], values["right"]) if profile == 0 else
                       (values["x"], values["x"]))
        return {"scores": [multiply(a, b) for a, b in zip(left, right, strict=True)]}
    if family == "linear":
        m, k, n = ((2, 3, 3), (1, 2, 2))[profile]
        projected = linear(values["x"], values["weight"], m, k, n)
        return {"scores": [f32(item + values["bias"][i % n])
                           for i, item in enumerate(projected)]}
    if family != "gated_mlp":
        raise ValueError("unknown oracle family")
    m, k, h, n = ((2, 3, 4, 2), (1, 2, 3, 3))[profile]
    value = [f32(item + values["bv"][i % h])
             for i, item in enumerate(linear(values["x"], values["wv"], m, k, h))]
    shifted = [f32(item + values["bg"][i % h])
               for i, item in enumerate(linear(values["x"], values["wg"], m, k, h))]
    gate = [0.0 if item < 0.0 else item for item in shifted]
    fused = [multiply(a, b) for a, b in zip(value, gate, strict=True)]
    projected = linear(fused, values["wo"], m, h, n)
    return {"scores": [f32(item + values["bout"][i % n])
                       for i, item in enumerate(projected)]}


def varied_batch():
    value = batch_data("linear", 0)
    value["requests"] = [value["requests"][i] for i in (2, 0, 1)]
    value["requests"][0]["id"] = "renamed_2"
    value["requests"][2]["inputs"]["x"][0] = f32(
        value["requests"][2]["inputs"]["x"][0] + 0.25)
    return value


def case_records(family, profile, batch):
    return [{"id": request["id"], "input_sha256": digest(encoded(merged_input(batch, request))),
             "expected_outputs": reference(family, profile, merged_input(batch, request))}
            for request in batch["requests"]]


def candidate():
    programs = []
    for family in FAMILIES:
        for profile in range(2):
            source, batch = graph(family, profile), batch_data(family, profile)
            inputs, outputs = public_bindings(source)
            programs.append({"id": f"{family}_{profile}", "family": family, "profile": profile,
                             "graph_sha256": digest(encoded(source)), "inputs": inputs,
                             "outputs": outputs, "batch_sha256": digest(encoded(batch)),
                             "cases": case_records(family, profile, batch)})
    variation = {"program_id": "linear_0", "batch_sha256": digest(encoded(varied_batch())),
                 "cases": case_records("linear", 0, varied_batch())}
    scalars = sum(len(case["expected_outputs"]["scores"])
                  for item in [*programs, variation] for case in item["cases"])
    if scalars != 96:
        raise ValueError("fixed batch corpus changed")
    return {"schema_version": SCHEMA, "status": "PASS", "native_execution_observed": False,
            "batch_runs": 0, "request_runs": 0, "scalar_checks": 0, "negative_controls": 0,
            "numeric_rejections": 0, "planned_batch_runs": 7, "planned_request_runs": 21,
            "planned_scalar_checks": 96, "planned_negative_controls": 6,
            "planned_numeric_rejections": 2, "programs": programs, "variation": variation}


def _write_fixtures(directory, report):
    snapshots = {}
    for program in report["programs"]:
        family, profile = program["family"], program["profile"]
        folder = directory / program["id"]
        folder.mkdir(mode=0o700)
        for name, payload in (("graph.json", encoded(graph(family, profile))),
                              ("batch.json", encoded(batch_data(family, profile)))):
            path = folder / name
            with path.open("xb") as stream:
                stream.write(payload)
            snapshots[path] = payload
    path = directory / "varied-batch.json"
    snapshots[path] = encoded(varied_batch())
    path.write_bytes(snapshots[path])
    return snapshots


def emit():
    report = candidate()
    parent = ROOT / "tmp"
    if parent.is_symlink():
        raise ValueError("fixture directory rejected")
    parent.mkdir(mode=0o700, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="batch-fixtures-", dir=parent))
    _write_fixtures(directory, report)
    report["fixture_directory"] = str(directory)
    (directory / "fixtures.json").write_bytes(encoded(report))
    return report


def _installed_cli():
    if sys.platform != "linux":
        raise ValueError("explicit CLI execution requires Linux")
    executable = Path(sys.executable).absolute().parent / "tuc-cpu-app"
    metadata = executable.lstat()
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o022 or
            not os.access(executable, os.X_OK)):
        raise ValueError("installed console script rejected")
    return executable


def _invoke(executable, arguments):
    """Drain fixed-command pipes within limits and terminate on timeout."""
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


def _response(result):
    code, output, error = result
    if code != 0 or error or len(output) > OUTPUT_LIMIT:
        raise ValueError("CLI success contract rejected")

    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate CLI key")
            value[key] = item
        return value

    def constant(_):
        raise ValueError("nonfinite CLI response rejected")

    return json.loads(output, object_pairs_hook=pairs, parse_constant=constant)


def _is_digest(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def request_digest(program_digest, bindings, data):
    payload = b"".join(struct.pack("<f", value) for binding in bindings
                       for value in data["inputs"][binding["public_name"]])
    return digest(bytes.fromhex(program_digest) + payload)


def batch_digest(program_digest, requests):
    value = {"schema_version": BATCH_SCHEMA, "program_digest": program_digest,
             "requests": [{"id": item["id"], "request_digest": item["request_digest"]}
                          for item in requests]}
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                             allow_nan=False).encode("ascii"))


def _inspect(result, program):
    value = _response(result)
    keys = {"schema_version", "action", "program_digest", "inputs", "outputs",
            "native_execution_observed"}
    if (type(value) is not dict or set(value) != keys or
            value["schema_version"] != "tuc.bounded_cpu_cli.v0" or value["action"] != "inspect" or
            value["native_execution_observed"] is not False or
            not _is_digest(value["program_digest"])):
        raise ValueError("inspect envelope rejected")
    options = {"sort_keys": True, "separators": (",", ":"), "allow_nan": False}
    if json.dumps([value["inputs"], value["outputs"]], **options) != json.dumps(
            [program["inputs"], program["outputs"]], **options):
        raise ValueError("independent public binding comparison failed")
    return value["program_digest"]


def _check_outputs(actual, expected):
    if type(actual) is not dict or list(actual) != list(expected):
        raise ValueError("public output identity changed")
    for name, values in expected.items():
        observed = actual[name]
        if (type(observed) is not list or len(observed) != len(values) or
                any(type(number) is not float or not math.isfinite(number)
                    for number in observed) or
                observed != values or any(struct.pack("<f", left) != struct.pack("<f", right)
                                         for left, right in zip(observed, values, strict=True))):
            raise ValueError("independent FP32 output comparison failed")
    return sum(map(len, expected.values()))


def _check_batch(result, program, batch, cases):
    value = _response(result)
    if (type(value) is not dict or set(value) != {
            "schema_version", "action", "program_digest", "batch_digest", "results",
            "native_execution_observed"} or value["schema_version"] != OUTPUT_SCHEMA or
            value["action"] != "run-batch" or value["native_execution_observed"] is not True or
            value["program_digest"] != program["program_digest"] or
            not _is_digest(value["batch_digest"]) or type(value["results"]) is not list or
            len(value["results"]) != len(batch["requests"]) or
            len(cases) != len(batch["requests"])):
        raise ValueError("batch output envelope rejected")
    expected_requests = []
    checked, scalars = [], 0
    for observed, request, case in zip(value["results"], batch["requests"], cases, strict=True):
        expected_digest = request_digest(program["program_digest"], program["inputs"],
                                         merged_input(batch, request))
        if (type(observed) is not dict or set(observed) != {"id", "request_digest", "outputs"} or
                observed["id"] != request["id"] or observed["id"] != case["id"] or
                observed["request_digest"] != expected_digest):
            raise ValueError("ordered request identity changed")
        scalars += _check_outputs(observed["outputs"], case["expected_outputs"])
        expected_requests.append({"id": request["id"], "request_digest": expected_digest})
        checked.append({**case, "request_digest": expected_digest, "outputs": observed["outputs"]})
    if batch_digest(program["program_digest"], expected_requests) != value["batch_digest"]:
        raise ValueError("batch digest changed")
    return checked, value["batch_digest"], scalars


def _unchanged(snapshots, workspace):
    if any(path.read_bytes() != value for path, value in snapshots.items()):
        raise ValueError("CLI changed an original fixture")
    if any(workspace.iterdir()):
        raise ValueError("CLI left application resources")


def negative_cases():
    base = batch_data("linear", 0)
    result = []
    for name in ("bad_last_input", "duplicate_ids", "shared_overlap", "wrong_shape", "max17"):
        value = copy.deepcopy(base)
        if name == "bad_last_input":
            value["requests"][-1]["inputs"] = {}
        elif name == "duplicate_ids":
            value["requests"][-1]["id"] = value["requests"][0]["id"]
        elif name == "shared_overlap":
            value["shared_inputs"]["x"] = value["requests"][0]["inputs"]["x"]
        elif name == "wrong_shape":
            value["requests"][0]["inputs"]["x"] = [1.0]
        else:
            value["requests"] = [{"id": f"sample_{i}", "inputs": base["requests"][0]["inputs"]}
                                 for i in range(17)]
        result.append({"id": name, "data": encoded(value), "reason": "batch_json_rejected"})
    result.append({"id": "malformed_json", "data": b'{"schema_version":',
                   "reason": "batch_json_rejected"})
    return result


def numeric_cases():
    result = []
    for name, index, bits in (("overflow_second", 1, 0x7f7fffff),
                              ("underflow_last", 2, 0x0d800000)):
        batch = batch_data("product", 1)
        number = struct.unpack("<f", struct.pack("<I", bits))[0]
        batch["requests"][index]["inputs"]["x"] = [number] + [0.0] * 5
        result.append({"id": name, "batch": batch, "request_index": index,
                       "reason": "numeric_rejection"})
    return result


def _controls(executable, directory, workspace, snapshots, programs):
    negative, numeric = [], []
    for case in negative_cases():
        path = directory / ("negative-" + case["id"] + ".json")
        with path.open("xb") as stream:
            stream.write(case["data"])
        snapshots[path] = case["data"]
        result = _invoke(executable, ("run-batch", str(directory / "linear_0/graph.json"),
                                     "--batch", str(path), "--workspace", str(workspace)))
        if result != (2, b"", f"tuc-cpu-app: {case['reason']}\n".encode("ascii")):
            raise ValueError("batch rejection contract failed: " + case["id"])
        _unchanged(snapshots, workspace)
        negative.append({"id": case["id"], "reason": case["reason"],
                         "batch_sha256": digest(case["data"])})
    program = next(item for item in programs if item["id"] == "product_1")
    for case in numeric_cases():
        raw = encoded(case["batch"])
        path = directory / ("numeric-" + case["id"] + ".json")
        with path.open("xb") as stream:
            stream.write(raw)
        snapshots[path] = raw
        result = _invoke(executable, ("run-batch", str(directory / "product_1/graph.json"),
                                     "--batch", str(path), "--workspace", str(workspace)))
        if result != (1, b"", b"tuc-cpu-app: numeric_rejection\n"):
            raise ValueError("batch numeric rejection failed: " + case["id"])
        _unchanged(snapshots, workspace)
        identities = [{"id": request["id"], "request_digest": request_digest(
            program["program_digest"], program["inputs"], merged_input(case["batch"], request))}
            for request in case["batch"]["requests"]]
        numeric.append({"id": case["id"], "reason": case["reason"],
                        "request_index": case["request_index"], "batch_sha256": digest(raw),
                        "program_digest": program["program_digest"],
                        "batch_digest": batch_digest(program["program_digest"], identities),
                        "requests": identities})
    return negative, numeric


def run():
    executable, report = _installed_cli(), candidate()
    scalar_checks = request_runs = 0
    with tempfile.TemporaryDirectory(prefix="tuc-batch-consumer-") as temporary:
        directory = Path(temporary)
        workspace = directory / "workspace"
        workspace.mkdir(mode=0o700)
        snapshots = _write_fixtures(directory, report)
        for program in report["programs"]:
            folder = directory / program["id"]
            program["program_digest"] = _inspect(
                _invoke(executable, ("inspect", str(folder / "graph.json"))), program)
            _unchanged(snapshots, workspace)
            batch = batch_data(program["family"], program["profile"])
            result = _invoke(executable, ("run-batch", str(folder / "graph.json"), "--batch",
                                         str(folder / "batch.json"), "--workspace", str(workspace)))
            cases, batch_hash, scalars = _check_batch(result, program, batch, program["cases"])
            program.update(cases=cases, batch_digest=batch_hash)
            scalar_checks += scalars
            request_runs += len(cases)
            _unchanged(snapshots, workspace)
        program, variation = report["programs"][0], report["variation"]
        result = _invoke(executable, ("run-batch", str(directory / "linear_0/graph.json"),
                                     "--batch",
                                     str(directory / "varied-batch.json"),
                                     "--workspace", str(workspace)))
        cases, batch_hash, scalars = _check_batch(
            result, program, varied_batch(), variation["cases"])
        variation.update(cases=cases, batch_digest=batch_hash,
                         program_digest=program["program_digest"])
        if (batch_hash == program["batch_digest"] or
                cases[0]["request_digest"] != program["cases"][2]["request_digest"] or
                cases[1]["request_digest"] != program["cases"][0]["request_digest"] or
                cases[2]["request_digest"] == program["cases"][1]["request_digest"]):
            raise ValueError("batch identity variation changed")
        scalar_checks += scalars
        request_runs += len(cases)
        _unchanged(snapshots, workspace)
        negative, numeric = _controls(
            executable, directory, workspace, snapshots, report["programs"])
    if (scalar_checks != 96 or request_runs != 21 or len(negative) != 6 or len(numeric) != 2 or
            len({item["program_digest"] for item in report["programs"]}) != 6):
        raise ValueError("batch coverage incomplete")
    report.update(native_execution_observed=True, batch_runs=7, request_runs=request_runs,
                  scalar_checks=scalar_checks, negative_controls=len(negative),
                  numeric_rejections=len(numeric), control_results=negative,
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
