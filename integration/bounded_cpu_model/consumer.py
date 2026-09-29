"""Independent installed model consumer; default is inert, --run is explicit."""

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
FAMILIES = ("linear", "classifier", "attention")
SCHEMA = "tuc.bounded_cpu_model_integration.v0"
MODEL_SCHEMA = "tuc.bounded_cpu_model.v0"
INPUT_SCHEMA = "tuc.bounded_cpu_inputs.v0"
BATCH_SCHEMA = "tuc.bounded_cpu_batch.v0"
CALL_TIMEOUT = 700.0
OUTPUT_LIMIT = 2 * 1024 * 1024
ERROR_LIMIT = 4096
RTOL, ATOL, MASS_ATOL = 2e-5, 2e-6, 8e-6


def encoded(value):
    return (
        json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")) + "\n"
    ).encode("ascii")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def f32(value):
    result = struct.unpack("<f", struct.pack("<f", value))[0]
    bits = struct.unpack("<I", struct.pack("<f", result))[0] & 0x7FFFFFFF
    exponent = bits & 0x7F800000
    if not math.isfinite(result) or (bits and not exponent):
        raise ValueError("oracle value is outside the checked FP32 domain")
    return result


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
        return {
            "public_name": public,
            "tensor_name": tensor,
            "tensor_index": names.index(tensor),
            "shape": shapes[tensor],
            "dtype": "float32",
        }

    return (
        [binding(name, name) for name in names if name not in produced],
        [binding(item["public_name"], item["tensor_name"]) for item in source["returns"]],
    )


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
        items = values[row * columns : (row + 1) * columns]
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


def _scaled_reference(family, profile, envelope):
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
        transposed = [
            values["value"][row * d + column] for column in range(d) for row in range(seq)
        ]
        result = _linear(probability, transposed, m, seq, d)
    else:
        raise ValueError("unknown fixed oracle family")
    return {"scores": result}


def _installed_cli():
    if sys.platform != "linux":
        raise ValueError("explicit CLI execution requires Linux")
    executable = Path(sys.executable).absolute().parent / "tuc-cpu-app"
    metadata = executable.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_mode & 0o022
        or not os.access(executable, os.X_OK)
    ):
        raise ValueError("installed console script rejected")
    return executable


def _invoke(executable, arguments):
    """Drain fixed-command pipes within limits and terminate on timeout."""
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONNOUSERSITE"] = "1"
    process = subprocess.Popen(
        (str(executable), *arguments),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        close_fds=True,
        env=environment,
    )
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
                    chunk = os.read(
                        key.fileobj.fileno(), min(65536, limit - len(buffers[key.data]) + 1)
                    )
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
    payload = b"".join(
        struct.pack("<f", value)
        for binding in bindings
        for value in data["inputs"][binding["public_name"]]
    )
    return digest(bytes.fromhex(program_digest) + payload)


def batch_digest(program_digest, requests):
    value = {
        "schema_version": BATCH_SCHEMA,
        "program_digest": program_digest,
        "requests": [
            {"id": item["id"], "request_digest": item["request_digest"]} for item in requests
        ],
    }
    return digest(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("ascii")
    )


def _unchanged(snapshots, workspace):
    if any(path.read_bytes() != value for path, value in snapshots.items()):
        raise ValueError("CLI changed an original fixture")
    if any(workspace.iterdir()):
        raise ValueError("CLI left application resources")


def graph(family, profile):
    if family not in FAMILIES or type(profile) is not int or profile not in (0, 1):
        raise ValueError("unknown model corpus")
    add, mul = {"elementwise_kind": "add"}, {"elementwise_kind": "mul"}
    if family == "attention":
        m, k, s, d = ((2, 4, 3, 2), (1, 2, 4, 3))[profile]
        tensors = (
            ("q", [m, k]),
            ("key", [s, k]),
            ("logits", [m, s]),
            ("scale", [1]),
            ("scaled", [m, s]),
            ("probability", [m, s]),
            ("value", [s, d]),
            ("y", [m, d]),
        )
        ops = (
            ("logits", "matmul", ["q", "key"], {"rhs_transposed": True}),
            ("scaled", "elementwise", ["logits", "scale"], mul),
            ("probability", "softmax", ["scaled"], {"axis": 1}),
            ("y", "matmul", ["probability", "value"], {}),
        )
    else:
        m, k, n = (((2, 3, 3), (1, 2, 2)) if family == "linear" else ((2, 3, 4), (1, 2, 3)))[
            profile
        ]
        tensors = (("x", [m, k]), ("weight", [n, k]), ("p", [m, n]), ("bias", [n]), ("y", [m, n]))
        ops = (
            ("p", "matmul", ["x", "weight"], {"rhs_transposed": True}),
            ("y", "elementwise", ["p", "bias"], add),
        )
        if family == "classifier":
            tensors = (
                ("x", [m, k]),
                ("gain", [k]),
                ("scaled", [m, k]),
                ("offset", [k]),
                ("calibrated", [m, k]),
                ("weight", [n, k]),
                ("p", [m, n]),
                ("bias", [n]),
                ("logits", [m, n]),
                ("y", [m, n]),
            )
            ops = (
                ("scaled", "elementwise", ["x", "gain"], mul),
                ("calibrated", "elementwise", ["scaled", "offset"], add),
                ("p", "matmul", ["calibrated", "weight"], {"rhs_transposed": True}),
                ("logits", "elementwise", ["p", "bias"], add),
                ("y", "softmax", ["logits"], {"axis": 1}),
            )
    return {
        "schema_version": "source_intent.v0",
        "name": f"model_{family}_{profile}",
        "tensors": [{"name": name, "shape": shape, "dtype": "float32"} for name, shape in tensors],
        "operations": [
            {
                "name": name,
                "family": kind,
                "inputs": names,
                "outputs": [name],
                "attributes": attrs,
                "hints": {},
            }
            for name, kind, names, attrs in ops
        ],
        "returns": [{"public_name": "scores", "tensor_name": "y", "required": True}],
    }


def data(family, profile, case):
    bindings, _ = public_bindings(graph(family, profile))
    variable = "q" if family == "attention" else "x"
    values = {
        item["public_name"]: [
            f32(
                (
                    (
                        i * 5
                        + slot * 3
                        + profile
                        + (case * 2 if item["public_name"] == variable else 0)
                    )
                    % 13
                    - 6
                )
                / 8
            )
            for i in range(math.prod(item["shape"]))
        ]
        for slot, item in enumerate(bindings)
    }
    if family == "classifier":
        values["gain"] = [0.5 + i * 0.25 for i in range(len(values["gain"]))]
    if family == "attention":
        values["scale"] = [0.5 if profile == 0 else 0.75]
    if family == "linear":
        values["bias"][-1] = -0.0
    return {"schema_version": INPUT_SCHEMA, "inputs": values}


def reference(family, profile, envelope):
    if family != "linear":
        return _scaled_reference(family, profile, envelope)
    m, k, n = ((2, 3, 3), (1, 2, 2))[profile]
    values = envelope["inputs"]
    result = _linear(values["x"], values["weight"], m, k, n)
    return {"scores": [f32(value + values["bias"][i % n]) for i, value in enumerate(result)]}


def fixed_parameters(family, profile):
    variable = "q" if family == "attention" else "x"
    return {
        name: values
        for name, values in data(family, profile, 0)["inputs"].items()
        if name != variable
    }


def variable_inputs(family, profile, case):
    name = "q" if family == "attention" else "x"
    return {
        "schema_version": INPUT_SCHEMA,
        "inputs": {name: data(family, profile, case)["inputs"][name]},
    }


def batch_data(family, profile):
    batch = {
        "schema_version": BATCH_SCHEMA,
        "requests": [
            {"id": f"sample_{i}", "inputs": variable_inputs(family, profile, i)["inputs"]}
            for i in range(2)
        ],
    }
    if family == "linear" and profile == 1:
        batch["shared_inputs"] = variable_inputs(family, profile, 0)["inputs"]
        for request in batch["requests"]:
            request["inputs"] = {}
    return batch


def model_identity(value):
    expected = {
        "schema_version": MODEL_SCHEMA,
        "graph": value["graph"],
        "parameter_bits": {
            name: b"".join(struct.pack("<f", v) for v in numbers).hex()
            for name, numbers in value["parameters"].items()
        },
    }
    return digest(
        json.dumps(
            expected, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("ascii")
    )


def _same(left, right):
    # Dict field order is not semantic, but number and boolean types are.
    if json.dumps(left, sort_keys=True, allow_nan=False) != json.dumps(
        right, sort_keys=True, allow_nan=False
    ):
        raise ValueError("independent identity mismatch")


def check_outputs(actual, expected, family, profile):
    if type(actual) is not dict or set(actual) != {"scores"}:
        raise ValueError("public output identity rejected")
    observed = actual["scores"]
    wanted = expected["scores"]
    if (
        type(observed) is not list
        or len(observed) != len(wanted)
        or any(type(n) is not float or not math.isfinite(n) for n in observed)
    ):
        raise ValueError("output shape or numeric domain rejected")
    for a, b in zip(observed, wanted, strict=True):
        if family == "linear":
            if struct.pack("<f", a) != struct.pack("<f", b):
                raise ValueError("bitwise FP32 output mismatch")
        elif abs(a - b) > ATOL + RTOL * abs(b):
            raise ValueError("composed numeric output mismatch")
    rows = 0
    if family == "classifier":
        rows, columns = ((2, 4), (1, 3))[profile]
        if any(not 0 < v <= 1 for v in observed) or any(
            abs(sum(observed[i * columns : (i + 1) * columns]) - 1) > MASS_ATOL for i in range(rows)
        ):
            raise ValueError("probability mass rejected")
    return len(wanted), rows


def candidate():
    return {
        "schema_version": SCHEMA,
        "status": "PASS",
        "native_execution_observed": False,
        "planned_models": 6,
        "planned_model_packs": 7,
        "planned_single_runs": 13,
        "planned_batch_runs": 6,
        "planned_batch_request_runs": 12,
        "planned_scalar_checks": 110,
        "planned_bitexact_scalar_checks": 38,
        "planned_tolerance_scalar_checks": 72,
        "planned_row_mass_checks": 12,
        "planned_negative_controls": 8,
        "planned_numeric_rejections": 2,
        "models": [
            {
                "id": f"{family}_{profile}",
                "graph_sha256": digest(encoded(graph(family, profile))),
                "parameters_sha256": digest(
                    encoded(
                        {
                            "schema_version": INPUT_SCHEMA,
                            "inputs": fixed_parameters(family, profile),
                        }
                    )
                ),
            }
            for family in FAMILIES
            for profile in range(2)
        ],
    }


def run():
    executable = _installed_cli()
    report = candidate()
    counts = {
        key: 0
        for key in (
            "model_packs",
            "single_runs",
            "batch_runs",
            "batch_request_runs",
            "scalar_checks",
            "bitexact_scalar_checks",
            "tolerance_scalar_checks",
            "row_mass_checks",
            "negative_controls",
            "numeric_rejections",
        )
    }
    with tempfile.TemporaryDirectory(prefix="tuc-model-consumer-") as folder:
        root = Path(folder)
        workspace = root / "workspace"
        workspace.mkdir(mode=0o700)
        snapshots = {}

        def write(name, value):
            path = root / name
            raw = value if type(value) is bytes else encoded(value)
            with path.open("xb") as stream:
                stream.write(raw)
            snapshots[path] = raw
            return str(path)

        def invoke(arguments):
            result = _invoke(executable, arguments)
            _unchanged(snapshots, workspace)
            return result

        def inspect_model(path, value, original):
            result = _response(invoke(["inspect-model", path]))
            fixed = value["parameters"]
            wanted = {
                "schema_version": "tuc.bounded_cpu_model_cli.v0",
                "action": "inspect-model",
                "program_digest": original["program_digest"],
                "model_digest": model_identity(value),
                "native_execution_observed": False,
                "inputs": [b for b in original["inputs"] if b["public_name"] not in fixed],
                "parameters": [b for b in original["inputs"] if b["public_name"] in fixed],
                "outputs": original["outputs"],
            }
            _same(result, wanted)
            return result

        def check_run(result, model_value, program, envelope, family, profile, action="run-model"):
            observed = _response(result)
            expected = reference(family, profile, envelope)
            wanted_digest = request_digest(program["program_digest"], program["inputs"], envelope)
            if (
                type(observed) is not dict
                or set(observed)
                != {
                    "schema_version",
                    "action",
                    "model_digest",
                    "program_digest",
                    "request_digest",
                    "outputs",
                    "native_execution_observed",
                }
                or observed["schema_version"] != "tuc.bounded_cpu_model_cli.v0"
                or observed["action"] != action
                or observed["native_execution_observed"] is not True
                or observed["program_digest"] != program["program_digest"]
                or observed["model_digest"] != model_identity(model_value)
                or observed["request_digest"] != wanted_digest
            ):
                raise ValueError("model result identity rejected")
            scalars, rows = check_outputs(observed["outputs"], expected, family, profile)
            counts["scalar_checks"] += scalars
            counts[
                "bitexact_scalar_checks" if family == "linear" else "tolerance_scalar_checks"
            ] += scalars
            counts["row_mass_checks"] += rows
            return {
                "input_sha256": digest(encoded(envelope)),
                "request_digest": wanted_digest,
                "expected_outputs": expected,
                "outputs": observed["outputs"],
            }

        records = []
        for family in FAMILIES:
            for profile in range(2):
                label = f"{family}_{profile}"
                g = graph(family, profile)
                graph_path = write(label + "-graph.json", g)
                fixed = fixed_parameters(family, profile)
                param_path = write(
                    label + "-params.json", {"schema_version": INPUT_SCHEMA, "inputs": fixed}
                )
                baseline = _response(invoke(["inspect", graph_path]))
                bindings, outputs = public_bindings(g)
                if not _is_digest(baseline.get("program_digest")):
                    raise ValueError("program identity rejected")
                _same(
                    baseline,
                    {
                        "schema_version": "tuc.bounded_cpu_cli.v0",
                        "action": "inspect",
                        "program_digest": baseline["program_digest"],
                        "inputs": bindings,
                        "outputs": outputs,
                        "native_execution_observed": False,
                    },
                )
                packed_result = invoke(["pack-model", graph_path, "--parameters", param_path])
                value = _response(packed_result)
                _same(value, {"schema_version": MODEL_SCHEMA, "graph": g, "parameters": fixed})
                canonical = (
                    json.dumps(
                        value,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode()
                    + b"\n"
                )
                if packed_result[1] != canonical:
                    raise ValueError("noncanonical packed model")
                model_path = write(label + "-model.json", canonical)
                inspected = inspect_model(model_path, value, baseline)
                counts["model_packs"] += 1
                item = {
                    "id": label,
                    "model_sha256": digest(canonical),
                    "graph_sha256": digest(encoded(g)),
                    "parameters_sha256": digest(
                        encoded({"schema_version": INPUT_SCHEMA, "inputs": fixed})
                    ),
                    "model_digest": inspected["model_digest"],
                    "program_digest": baseline["program_digest"],
                    "cases": [],
                }
                for case in range(2):
                    path = write(
                        f"{label}-input-{case}.json", variable_inputs(family, profile, case)
                    )
                    result = invoke(
                        ["run-model", model_path, "--inputs", path, "--workspace", str(workspace)]
                    )
                    item["cases"].append(
                        check_run(
                            result, value, baseline, data(family, profile, case), family, profile
                        )
                    )
                    counts["single_runs"] += 1
                batch = batch_data(family, profile)
                batch_path = write(label + "-batch.json", batch)
                result = _response(
                    invoke(
                        [
                            "run-model-batch",
                            model_path,
                            "--batch",
                            batch_path,
                            "--workspace",
                            str(workspace),
                        ]
                    )
                )
                if (
                    type(result) is not dict
                    or set(result)
                    != {
                        "schema_version",
                        "action",
                        "model_digest",
                        "program_digest",
                        "batch_digest",
                        "results",
                        "native_execution_observed",
                    }
                    or result["schema_version"] != "tuc.bounded_cpu_model_batch_cli.v0"
                    or result["action"] != "run-model-batch"
                    or result["native_execution_observed"] is not True
                    or result["program_digest"] != baseline["program_digest"]
                    or result["model_digest"] != inspected["model_digest"]
                    or type(result["results"]) is not list
                    or len(result["results"]) != 2
                ):
                    raise ValueError("model batch envelope rejected")
                requests = []
                for request, observed in zip(batch["requests"], result["results"], strict=True):
                    if (
                        set(observed) != {"id", "request_digest", "outputs"}
                        or observed["id"] != request["id"]
                    ):
                        raise ValueError("batch order rejected")
                    expanded = {
                        "schema_version": INPUT_SCHEMA,
                        "inputs": {**fixed, **batch.get("shared_inputs", {}), **request["inputs"]},
                    }
                    checked = check_run(
                        (
                            0,
                            encoded(
                                {
                                    "schema_version": "tuc.bounded_cpu_model_cli.v0",
                                    "action": "run-model",
                                    "model_digest": result["model_digest"],
                                    "program_digest": result["program_digest"],
                                    "request_digest": observed["request_digest"],
                                    "outputs": observed["outputs"],
                                    "native_execution_observed": True,
                                }
                            ),
                            b"",
                        ),
                        value,
                        baseline,
                        expanded,
                        family,
                        profile,
                    )
                    requests.append({"id": request["id"], **checked})
                if result["batch_digest"] != batch_digest(baseline["program_digest"], requests):
                    raise ValueError("model batch digest rejected")
                item["batch"] = {
                    "batch_sha256": digest(encoded(batch)),
                    "batch_digest": result["batch_digest"],
                    "requests": requests,
                }
                counts["batch_runs"] += 1
                counts["batch_request_runs"] += 2
                records.append(item)
                if family == "linear" and profile == 0:
                    saved = (g, value, baseline, model_path, graph_path)

        g, original, baseline, original_path, graph_path = saved
        changed = copy.deepcopy(original)
        changed["parameters"]["weight"][0] += 0.5
        parameter_path = write(
            "changed-params.json", {"schema_version": INPUT_SCHEMA, "inputs": changed["parameters"]}
        )
        changed_result = invoke(["pack-model", graph_path, "--parameters", parameter_path])
        _same(_response(changed_result), changed)
        changed_path = write("changed-model.json", changed_result[1])
        changed_inspect = inspect_model(changed_path, changed, baseline)
        if changed_inspect["model_digest"] == model_identity(original):
            raise ValueError("changed parameter did not change model identity")
        expanded = data("linear", 0, 0)
        expanded["inputs"].update(changed["parameters"])
        variable_path = write("changed-input.json", variable_inputs("linear", 0, 0))
        report["parameter_variant"] = {
            "model_digest": model_identity(changed),
            "model_sha256": digest(changed_result[1]),
            "program_digest": baseline["program_digest"],
            **check_run(
                invoke(
                    [
                        "run-model",
                        changed_path,
                        "--inputs",
                        variable_path,
                        "--workspace",
                        str(workspace),
                    ]
                ),
                changed,
                baseline,
                expanded,
                "linear",
                0,
            ),
        }
        counts["model_packs"] += 1
        counts["single_runs"] += 1
        controls = []
        for number, kind in enumerate(
            (
                "duplicate",
                "external_path",
                "bad_extent",
                "subnormal",
                "no_variables",
                "override",
                "last_override",
                "last_extent",
            )
        ):
            bad = copy.deepcopy(original)
            action, flag = "inspect-model", None
            if kind == "duplicate":
                payload = encoded(bad).replace(
                    b'"parameters":', b'"parameters":{},"parameters":', 1
                )
            else:
                if kind == "external_path":
                    bad["path"] = "untrusted-path"
                elif kind == "bad_extent":
                    bad["parameters"]["weight"] = [1.0]
                elif kind == "subnormal":
                    bad["parameters"]["weight"][0] = 1e-40
                elif kind == "no_variables":
                    bad["parameters"]["x"] = [0.0] * 6
                elif kind == "override":
                    action, flag = "run-model", "--inputs"
                    bad = variable_inputs("linear", 0, 0)
                    bad["inputs"]["bias"] = original["parameters"]["bias"]
                elif kind in ("last_override", "last_extent"):
                    action, flag = "run-model-batch", "--batch"
                    bad = batch_data("linear", 0)
                    bad["requests"][-1]["inputs"].update(
                        {"bias": original["parameters"]["bias"]}
                        if kind == "last_override"
                        else {"x": [1.0]}
                    )
                payload = encoded(bad)
            bad_path = write(f"bad-{number}.json", payload)
            args = (
                [action, bad_path]
                if flag is None
                else [action, original_path, flag, bad_path, "--workspace", str(workspace)]
            )
            reason = "batch_json_rejected" if kind == "last_extent" else "model_json_rejected"
            if invoke(args) != (2, b"", f"tuc-cpu-app: {reason}\n".encode()):
                raise ValueError("model negative control not rejected")
            controls.append({"id": kind, "payload_sha256": digest(payload), "reason": reason})
        report["negative_control_records"] = controls
        counts["negative_controls"] = len(controls)
        numeric = copy.deepcopy(original)
        numeric["parameters"]["weight"][0] = 2.0
        numeric_path = write("numeric-model.json", numeric)
        numeric_inspect = inspect_model(numeric_path, numeric, baseline)
        max_float = struct.unpack("<f", struct.pack("<I", 0x7F7FFFFF))[0]
        bad_input = {
            "schema_version": INPUT_SCHEMA,
            "inputs": {"x": [max_float, 0.0, 0.0, 0.0, 0.0, 0.0]},
        }
        bad_batch = {
            "schema_version": BATCH_SCHEMA,
            "requests": [
                {"id": "first", "inputs": variable_inputs("linear", 0, 0)["inputs"]},
                {"id": "last", "inputs": bad_input["inputs"]},
            ],
        }
        report["numeric_controls"] = []
        for action, flag, payload in (
            ("run-model", "--inputs", bad_input),
            ("run-model-batch", "--batch", bad_batch),
        ):
            path = write(action + "-numeric.json", payload)
            if invoke([action, numeric_path, flag, path, "--workspace", str(workspace)]) != (
                1,
                b"",
                b"tuc-cpu-app: numeric_rejection\n",
            ):
                raise ValueError("numeric model control not rejected")
            requests = (
                payload["requests"]
                if action.endswith("batch")
                else [{"id": "single", "inputs": payload["inputs"]}]
            )
            identities = [
                {
                    "id": item["id"],
                    "request_digest": request_digest(
                        baseline["program_digest"],
                        baseline["inputs"],
                        {"inputs": {**numeric["parameters"], **item["inputs"]}},
                    ),
                }
                for item in requests
            ]
            report["numeric_controls"].append(
                {
                    "action": action,
                    "payload_sha256": digest(encoded(payload)),
                    "model_digest": numeric_inspect["model_digest"],
                    "requests": identities,
                    "batch_digest": batch_digest(baseline["program_digest"], identities)
                    if action.endswith("batch")
                    else None,
                    "reason": "numeric_rejection",
                }
            )
            counts["numeric_rejections"] += 1
        _unchanged(snapshots, workspace)
        for key, value in counts.items():
            if value != report["planned_" + key]:
                raise ValueError("fixed model corpus count drift")
        report.update(counts)
        report.update(
            {
                "models": records,
                "native_execution_observed": True,
                "original_files_unchanged": True,
                "workspaces_clean": True,
            }
        )
    with (ROOT / "record.json").open("xb") as stream:
        stream.write(encoded(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="execute the installed CPU console")
    args = parser.parse_args()
    print(json.dumps(run() if args.run else candidate(), sort_keys=True))


if __name__ == "__main__":
    main()
