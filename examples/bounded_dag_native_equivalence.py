"""Pure, bounded comparison of fixed-portfolio native DAG records.

The records describe earlier operator runs. This verifier reconstructs their
source binding and checks the protocol; it never executes a worker or proves
that an otherwise fabricated record came from a physical device.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from examples import bounded_dag_native as native

MAX_RECORD_BYTES = 256 * 1024
MAX_DEPTH = 4
MAX_NODES = 10_000
MAX_MEMBERS = 206
MAX_STRING = 128
MAX_INTEGER = 1_000_000
PROFILES = ("cpu", "gpu", "mixed")
RECORD_SCHEMA = "tuc.bounded_dag_native_record.v0"


def _reject():
    raise ValueError("bounded DAG native comparison rejected")


def _bounded_metadata(value):
    remaining = MAX_NODES

    def visit(item, depth):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > MAX_DEPTH:
            _reject()
        if type(item) is dict:
            if len(item) > MAX_MEMBERS:
                _reject()
            for key, child in item.items():
                if type(key) is not str:
                    _reject()
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif type(item) is str:
            if len(item) > MAX_STRING or len(item.encode("utf-8")) > MAX_STRING:
                _reject()
        elif type(item) is int:
            if not 0 <= item <= MAX_INTEGER:
                _reject()
        elif item is not None and type(item) is not bool:
            _reject()

    visit(value, 0)
    if len(native._json(value).encode("utf-8")) > MAX_RECORD_BYTES:
        _reject()


def _json_record(text):
    """Bound nesting before JSON decoding; reject duplicate keys and numbers."""
    if type(text) is not str or len(text.encode("utf-8")) > MAX_RECORD_BYTES:
        _reject()
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                _reject()
        elif char in "]}":
            depth -= 1

    def pairs(items):
        if len(items) > MAX_MEMBERS:
            _reject()
        result = {}
        for key, value in items:
            if key in result:
                _reject()
            result[key] = value
        return result

    def integer(token):
        if len(token) > 7:
            _reject()
        value = int(token)
        if not 0 <= value <= MAX_INTEGER:
            _reject()
        return value

    def no_float(_token):
        _reject()

    value = json.loads(text, object_pairs_hook=pairs, parse_int=integer,
                       parse_float=no_float, parse_constant=no_float)
    _bounded_metadata(value)
    return value


def load_record(path):
    """Read at most 256 KiB from a regular, non-symlink UTF-8 record file."""
    return _json_record(native._read(Path(path), MAX_RECORD_BYTES))


def _exact(value, expected):
    if type(value) is not type(expected):
        _reject()
    if type(expected) is dict:
        if set(value) != set(expected):
            _reject()
        for key in expected:
            _exact(value[key], expected[key])
    elif value != expected:
        _reject()


def _flat_shape(value, expected):
    if (type(value) is not dict or set(value) != set(expected) or
            any(type(value[key]) is not type(expected[key]) for key in expected)):
        _reject()


def _receipt_names(worker):
    names = set()
    builds = ("static", "sanitized") if worker == "c11" else ("matrix",)
    for build in builds:
        for index in (range(0, 36, 3) if worker == "c11" else range(36)):
            suffixes = ["preflight", "execute", "fault1", "fault2", "fault3"]
            if index % 3:
                suffixes.append("fault4")
            names.update(f"{build}-{index}-{suffix}.json" for suffix in suffixes)
        names.update(f"{build}-invalid-{kind}.json" for kind in ("plan", "mode"))
    if worker == "c11":
        names.add("sanitized-contract.json")
    return names


def _prepare_record(value, worker):
    """Reject malformed records before running the pure compiler reconstruction."""
    if type(worker) is not str or worker not in ("c11", "matrix"):
        _reject()
    _bounded_metadata(value)
    fixed = {
        "schema_version": RECORD_SCHEMA, "status": "PASS", "graphs": 12, "plans": 36,
        "worker": worker, "native_execution_observed": True,
        "cuda_execution_observed": worker == "matrix", "normal_runtime_admission": False,
        "latency_ns": None, "energy_pj": None, "observation_scope": "fixed_portfolio_only",
    }
    variable = {"context_digest", "expected_matrix_counters", "image_ids", "observations"}
    if type(value) is not dict or set(value) != set(fixed) | variable:
        _reject()
    for key, expected in fixed.items():
        _exact(value[key], expected)
    if (type(value["context_digest"]) is not str or
            re.fullmatch(r"sha256:[0-9a-f]{64}", value["context_digest"]) is None):
        _reject()
    _flat_shape(value["expected_matrix_counters"], dict.fromkeys(native.COUNTERS, 0))
    images = value["image_ids"]
    builds = {"static", "sanitized"} if worker == "c11" else {"matrix"}
    if (type(images) is not dict or set(images) != builds or
            any(type(image) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image) is None
                for image in images.values())):
        _reject()
    observations = value["observations"]
    if type(observations) is not dict or set(observations) != _receipt_names(worker):
        _reject()
    for name, observation in observations.items():
        if name == "sanitized-contract.json":
            _exact(observation, {
                "schema_version": "tuc.bounded_dag_native_contract.v0", "status": "PASS",
                "plans": 36, "mutation_checks": 194688,
            })
        else:
            _flat_shape(observation, native.invalid_receipt(worker))


def _manifest_counters(manifest):
    """Independently count six baseline traversals of the normalized schedule."""
    counts = dict.fromkeys(native.COUNTERS, 0)
    counts["case_runs"] = 6
    for event in manifest["events"]:
        if event["kind"] == "execute":
            gpu = event["target"] == "cuda-sm86"
            counts["gpu_calls" if gpu else "cpu_calls"] += 6
            if gpu:
                counts["validation_download_calls"] += 6
                counts["validation_download_bytes"] += (
                    6 * manifest["buffers"][event["outputs"][0]]["bytes"]
                )
        elif event["kind"] == "copy":
            destination = manifest["buffers"][event["outputs"][0]]
            direction = "upload" if destination["space"] == "accelerator" else "download"
            counts[direction + "_calls"] += 6
            counts[direction + "_bytes"] += 6 * destination["bytes"]
        elif event["kind"] == "publish_output":
            counts["published_outputs"] += 6
            counts["scalar_checks"] += 6 * manifest["buffers"][event["inputs"][0]]["bytes"] // 4
    return counts


def _sum_counters(values):
    return {key: sum(value[key] for value in values) for key in native.COUNTERS}


def _reconstruct():
    rows = native.bundles()
    # One hardware-neutral graph and identical primitive sources per placement.
    for graph in range(12):
        variants = rows[graph * 3:graph * 3 + 3]
        if len({row[4]["hac_ir_digest"] for row in variants}) != 1:
            _reject()
        for name in ("generated.h", "generated.c", "kernels.cuh"):
            if len({row[3].files()[name] for row in variants}) != 1:
                _reject()
    context_digest = native._digest(native._json(native.artifact_files(rows)))
    counts = [_manifest_counters(row[4]) for row in rows]
    return rows, context_digest, counts


def _validate_record(value, worker, reconstructed):
    rows, context_digest, counts = reconstructed
    _exact(value["context_digest"], context_digest)
    _exact(value["expected_matrix_counters"], _sum_counters(counts))
    _exact(value["observations"], native.expected_files(worker, rows))
    for build in (("static", "sanitized") if worker == "c11" else ("matrix",)):
        for index in (range(0, 36, 3) if worker == "c11" else range(36)):
            observation = value["observations"][f"{build}-{index}-execute.json"]
            _exact({key: observation[key] for key in native.COUNTERS}, counts[index])


def validate_record(value, worker):
    """Validate a single complete record against the current bound source tree."""
    _prepare_record(value, worker)
    _validate_record(value, worker, _reconstruct())
    return value


def compare_records(c11, matrix):
    """Compare validated prior observations without admitting a runtime path."""
    for value, worker in ((c11, "c11"), (matrix, "matrix")):
        _prepare_record(value, worker)
    reconstructed = _reconstruct()
    for value, worker in ((c11, "c11"), (matrix, "matrix")):
        _validate_record(value, worker, reconstructed)
    for index in range(0, 36, 3):
        reference = matrix["observations"][f"matrix-{index}-execute.json"]
        for build in ("static", "sanitized"):
            observed = c11["observations"][f"{build}-{index}-execute.json"]
            _exact({**observed, "worker": "matrix"}, reference)
    profiles = {
        profile: _sum_counters([
            matrix["observations"][f"matrix-{index}-execute.json"]
            for index in range(offset, 36, 3)
        ]) for offset, profile in enumerate(PROFILES)
    }
    cpu_builds = {
        build: _sum_counters([
            c11["observations"][f"{build}-{index}-execute.json"]
            for index in range(0, 36, 3)
        ]) for build in ("static", "sanitized")
    }
    return {
        "schema_version": "tuc.bounded_dag_native_comparison.v0", "status": "PASS",
        "context_digest": reconstructed[1], "graphs": 12, "plans": 36,
        "receipt_counts": {"c11": len(c11["observations"]),
                           "matrix": len(matrix["observations"])},
        "fault_controls": {"c11": 72, "matrix": 132},
        "invalid_invocation_controls": {"c11": 4, "matrix": 2},
        "c11_baseline_counters": cpu_builds, "matrix_profile_counters": profiles,
        "matrix_counters": _sum_counters(list(profiles.values())),
        "cpu_baselines_equal": True, "one_matrix_image": True,
        "c11_image_ids": dict(c11["image_ids"]),
        "matrix_image_id": matrix["image_ids"]["matrix"],
        "c11_record_digest": native._digest(native._json(c11)),
        "matrix_record_digest": native._digest(native._json(matrix)),
        "verification_scope": "record_validation_only",
        "observation_scope": "fixed_portfolio_only", "normal_runtime_admission": False,
        "latency_ns": None, "energy_pj": None,
        "blocked_claims": ["arbitrary_inputs", "dynamic_shapes", "general_native_runtime",
                           "concurrent_execution", "performance", "independent_reproduction"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, nargs=2, metavar=("C11", "MATRIX"))
    args = parser.parse_args()
    try:
        print(json.dumps(compare_records(*(load_record(path) for path in args.records)),
                         indent=2, sort_keys=True, allow_nan=False))
    except (OSError, ValueError):
        print("bounded DAG native comparison rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
