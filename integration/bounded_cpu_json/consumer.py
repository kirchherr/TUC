"""Standalone installed-CLI conformance; default and --emit never invoke TUC.

Only --run executes the fixed console script beside this Python interpreter.
The graphs, input corpora and scalar FP32 oracle are owned by this client.
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
FAMILIES = ("fanout", "truefanin", "relu_sum")
PROFILES = ((2, 3, 2), (3, 2, 3))
SCHEMA = "tuc.bounded_cpu_json_integration.v0"
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
        raise ValueError("unknown fixed graph case")
    m, k, n = PROFILES[profile]
    if family == "fanout":
        tensors = (("a", (m, k)), ("b", (k, n)), ("p", (m, n)),
                   ("positive", (m, n)), ("rows", (m,)))
        operations = [("project", "matmul", ["a", "b"], "p", {}),
                      ("activate", "elementwise", ["p"], "positive",
                       {"elementwise_kind": "relu"}),
                      ("sum_raw", "reduction", ["p"], "rows", {"axis": 1})]
        returns = (("z_positive", "positive"), ("a_rows", "rows"))
    elif family == "truefanin":
        tensors = (("a", (m, k)), ("b", (k, n)), ("left", (m, n)),
                   ("c", (n, k)), ("d", (k, m)), ("right", (n, m)),
                   ("joined", (m, m)), ("rows", (m,)))
        operations = [("left_project", "matmul", ["a", "b"], "left", {}),
                      ("right_project", "matmul", ["c", "d"], "right", {}),
                      ("join", "matmul", ["left", "right"], "joined", {}),
                      ("sum_join", "reduction", ["joined"], "rows", {"axis": 1})]
        returns = (("joined_rows", "rows"),)
    else:
        tensors = (("x", (m, n)), ("positive", (m, n)), ("rows", (m,)))
        operations = [("activate", "elementwise", ["x"], "positive",
                       {"elementwise_kind": "relu"}),
                      ("sum_positive", "reduction", ["positive"], "rows", {"axis": 1})]
        returns = (("positive_rows", "rows"),)
    return {
        "schema_version": "source_intent.v0", "name": f"json_{family}_{profile}",
        "tensors": [{"name": name, "shape": list(shape), "dtype": "float32"}
                    for name, shape in tensors],
        "operations": [{"name": name, "family": kind, "inputs": inputs,
                        "outputs": [output], "attributes": attributes}
                       for name, kind, inputs, output, attributes in operations],
        "returns": [{"public_name": public, "tensor_name": tensor, "required": True}
                    for public, tensor in returns],
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


def _sums(values, rows, columns):
    result = []
    for row in range(rows):
        accumulator = 0.0
        for column in range(columns):
            accumulator = f32(accumulator + values[row * columns + column])
        result.append(accumulator)
    return result


def reference(family, profile, envelope):
    """Explicit family arithmetic, independent of graph/CLI operation metadata."""
    m, k, n = PROFILES[profile]
    values = envelope["inputs"]
    if family == "fanout":
        projected = _matmul(values["a"], values["b"], m, k, n)
        return {"z_positive": [max(0.0, value) for value in projected],
                "a_rows": _sums(projected, m, n)}
    if family == "truefanin":
        left = _matmul(values["a"], values["b"], m, k, n)
        right = _matmul(values["c"], values["d"], n, k, m)
        joined = _matmul(left, right, m, n, m)
        return {"joined_rows": _sums(joined, m, m)}
    if family == "relu_sum":
        return {"positive_rows": _sums([max(0.0, value) for value in values["x"]], m, n)}
    raise ValueError("unknown fixed graph family")


def candidate():
    programs = []
    scalar_checks = 0
    for family in FAMILIES:
        for profile in range(len(PROFILES)):
            source = graph(family, profile)
            inputs, outputs = public_bindings(source)
            cases = []
            for case in range(2):
                data = input_envelope(family, profile, case)
                expected = reference(family, profile, data)
                scalar_checks += sum(map(len, expected.values()))
                cases.append({"case": case, "input_sha256": digest(encoded(data)),
                              "expected_outputs": expected})
            programs.append({"id": f"{family}_{profile}", "family": family, "profile": profile,
                             "source_sha256": digest(encoded(source)), "inputs": inputs,
                             "outputs": outputs, "cases": cases})
    if scalar_checks != 56:
        raise ValueError("fixed corpus coverage changed")
    return {"schema_version": SCHEMA, "status": "PASS", "native_execution_observed": False,
            "case_runs": 0, "scalar_checks": 0, "numeric_rejections": 0, "negative_controls": 0,
            "planned_case_runs": 12, "planned_scalar_checks": scalar_checks,
            "planned_numeric_rejections": 1, "planned_negative_controls": 6,
            "programs": programs}


def _write_fixtures(directory, report):
    snapshots = {}
    for program in report["programs"]:
        folder = directory / program["id"]
        folder.mkdir(mode=0o700)
        files = {"graph.json": encoded(graph(program["family"], program["profile"]))}
        files.update({f"inputs-{case}.json": encoded(input_envelope(
            program["family"], program["profile"], case)) for case in range(2)})
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
    directory = Path(tempfile.mkdtemp(prefix="cli-fixtures-", dir=parent))
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
                observed != values):
            raise ValueError("independent scalar FP32 comparison failed")
    return sum(map(len, expected.values()))


def _rejected(executable, arguments, reason, exit_code=2):
    code, output, error = _invoke(executable, arguments)
    if code != exit_code or output or error != f"tuc-cpu-app: {reason}\n".encode("ascii"):
        raise ValueError("CLI rejection contract failed")


def _negative_controls(executable, directory, workspace, snapshots):
    folder = directory / "fanout_0"
    original_graph, original_input = folder / "graph.json", folder / "inputs-0.json"
    controls = []
    for kind, original, reason in (("graph", original_graph, "graph_json_rejected"),
                                   ("input", original_input, "input_json_rejected")):
        raw = original.read_bytes()
        schema = json.loads(raw)["schema_version"]
        duplicate = b'{"schema_version":' + json.dumps(schema).encode("ascii") + b"," + raw[1:]
        bad_files = (("duplicate", duplicate),
                     ("malformed", raw[:-3]))
        for label, payload in bad_files:
            path = directory / f"{label}-{kind}.json"
            path.write_bytes(payload)
            snapshots[path] = payload
            arguments = (("inspect", str(path)) if kind == "graph" else
                         ("run", str(original_graph), "--inputs", str(path),
                          "--workspace", str(workspace)))
            _rejected(executable, arguments, reason)
            _unchanged(snapshots, workspace)
            controls.append({"id": f"{label}_{kind}", "reason": reason})
        link = directory / f"symlink-{kind}.json"
        link.symlink_to(original)
        arguments = (("inspect", str(link)) if kind == "graph" else
                     ("run", str(original_graph), "--inputs", str(link),
                      "--workspace", str(workspace)))
        _rejected(executable, arguments, "file_rejected")
        _unchanged(snapshots, workspace)
        if not link.is_symlink() or link.read_bytes() != raw:
            raise ValueError("CLI changed a rejected symlink fixture")
        controls.append({"id": f"symlink_{kind}", "reason": "file_rejected"})
    return controls


def run():
    executable = _installed_cli()
    report = candidate()
    scalar_checks, case_runs = 0, 0
    with tempfile.TemporaryDirectory(prefix="tuc-json-cli-consumer-") as temporary:
        directory = Path(temporary)
        workspace = directory / "workspace"
        workspace.mkdir(mode=0o700)
        snapshots = _write_fixtures(directory, report)
        for program in report["programs"]:
            folder = directory / program["id"]
            graph_path = folder / "graph.json"
            inspected = _success(_invoke(executable, ("inspect", str(graph_path))), "inspect")
            if (inspected["inputs"] != program["inputs"] or
                    inspected["outputs"] != program["outputs"]):
                raise ValueError("independent public binding comparison failed")
            program["program_digest"] = inspected["program_digest"]
            _unchanged(snapshots, workspace)
            requests = set()
            for case in program["cases"]:
                input_path = folder / f"inputs-{case['case']}.json"
                actual = _success(_invoke(executable, (
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
        control_results = _negative_controls(executable, directory, workspace, snapshots)
        overflow = input_envelope("fanout", 0, 0)
        overflow["inputs"]["a"] = [f32(3.4028234663852886e38)] * 6
        overflow["inputs"]["b"] = [2.0] * 6
        overflow_path = directory / "numeric-overflow.json"
        snapshots[overflow_path] = encoded(overflow)
        overflow_path.write_bytes(snapshots[overflow_path])
        _rejected(executable, ("run", str(directory / "fanout_0" / "graph.json"),
                              "--inputs", str(overflow_path), "--workspace", str(workspace)),
                  "numeric_rejection", 1)
        _unchanged(snapshots, workspace)
        report["numeric_control"] = {"reason": "numeric_rejection",
                                     "input_sha256": digest(snapshots[overflow_path])}
    if (case_runs != 12 or scalar_checks != 56 or len(control_results) != 6 or
            len({program["program_digest"] for program in report["programs"]}) != 6):
        raise ValueError("CLI execution coverage incomplete")
    report.update(native_execution_observed=True, case_runs=case_runs, scalar_checks=scalar_checks,
                  numeric_rejections=1, negative_controls=len(control_results),
                  control_results=control_results, original_files_unchanged=True,
                  workspaces_clean=True)
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
