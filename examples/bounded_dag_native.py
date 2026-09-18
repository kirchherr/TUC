"""Prepare and verify a fixed native DAG portfolio; never launch native code.

The default command emits a non-admitting candidate report. --emit writes a
private reviewed build context. Only the separate operator executes workers;
physical GPU runs require fresh approval for the concrete source payload.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from hashlib import sha256
from pathlib import Path

from examples import bounded_dag_c11 as oracle
from examples import bounded_dag_compiler as portfolio
from tuc.backends.bounded_dag import DAGTarget, validate_bounded_dag_artifacts

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "docker/bounded-dag-native"
MAX_FILE_BYTES = 256 * 1024
MAX_CONTEXT_BYTES = 4 * 1024 * 1024
SCHEMA = "tuc.bounded_dag_native_observation.v0"
SUPPORT_FILES = (
    "abi.h", "contract.c", "contract_test.c", "worker.h", "host.c", "device.cu",
    "Dockerfile", "Dockerfile.dockerignore", "build-c11.sh", "build-cuda.sh", "operator.sh",
)
SOURCE_BINDINGS = (
    "examples/bounded_dag_native.py", "examples/bounded_dag_compiler.py",
    "examples/bounded_dag_c11.py", "src/tuc/backends/bounded_dag.py",
    "src/tuc/backends/bounded_dag_codegen.py", "src/tuc/runtime/residency.py",
    ".github/workflows/bounded-dag-native-proof.yml",
)
COUNTERS = (
    "case_runs", "cpu_calls", "gpu_calls", "scalar_checks", "published_outputs",
    "upload_calls", "upload_bytes", "download_calls", "download_bytes",
    "validation_download_calls", "validation_download_bytes",
)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(text):
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


def _read(path, limit=MAX_FILE_BYTES):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("native DAG regular bounded file required")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("native DAG file budget exceeded")
    return data.decode("utf-8")


def bundles():
    """Reconstruct all 36 immutable plans and revalidate their artifact texts."""
    result = []
    for family in portfolio.FAMILIES:
        for shape in portfolio.SHAPES:
            count = len(portfolio.graph_for(family, shape).operations)
            for profile in ("c" * count, "g" * count, ("gc" * count)[:count]):
                compilation, artifacts = portfolio.compile_case(family, profile, shape)
                targets = {assignment.backend_name: (
                    DAGTarget.C11 if assignment.backend_name == "dag-c11" else DAGTarget.CUDA_SM86
                ) for assignment in compilation.partition_plan.assignments}
                validate_bounded_dag_artifacts(
                    artifacts, compilation.hac_ir, compilation.partition_plan, targets
                )
                manifest = json.loads(artifacts.manifest_json)
                if (len(manifest["tensors"]) > 10 or len(manifest["operations"]) > 7 or
                        len(manifest["buffers"]) > 16 or len(manifest["events"]) > 18 or
                        manifest["planned_buffer_bytes"] > 7432 or
                        manifest["planned_copy_bytes"] > 2656 or
                        len(manifest["input_tensors"]) > 3 or
                        len(manifest["output_tensors"]) > 2):
                    raise ValueError("native DAG fixed portfolio budget changed")
                result.append((family, shape, profile, artifacts, manifest))
    if len(result) != 36:
        raise ValueError("native DAG fixed portfolio changed")
    return result


def _array(values):
    # Bound the entire expansion, including repeatedly referenced containers.
    # 4096 nodes of at most eight characters also bound output below 64 KiB.
    remaining = 4096

    def render(items, depth):
        nonlocal remaining
        remaining -= 1
        if (remaining < 0 or type(items) not in (list, tuple) or
                len(items) > 96 or depth > 4):
            raise ValueError("native DAG initializer rejected")
        fields = []
        for value in items:
            if type(value) in (list, tuple):
                fields.append(render(value, depth + 1))
            elif type(value) is int and 0 <= value <= 1_000_000:
                remaining -= 1
                if remaining < 0:
                    raise ValueError("native DAG initializer expansion rejected")
                fields.append(f"{value}U")
            else:
                raise ValueError("native DAG initializer field rejected")
        return "{" + ",".join(fields) + "}"

    return render(values, 0)


def _graph_initializer(manifest):
    tensors = [[len(t["shape"]), t["shape"][0],
                t["shape"][1] if len(t["shape"]) == 2 else 1, t["bytes"]]
               for t in manifest["tensors"]]
    operations = [[{"matmul": 0, "relu": 1, "sum_axis1": 2}[op["kind"]],
                   op["inputs"][0], op["inputs"][1] if len(op["inputs"]) == 2 else 255,
                   op["outputs"][0], op["launch"]["blocks"], op["launch"]["threads_per_block"]]
                  for op in manifest["operations"]]
    inputs, outputs = manifest["input_tensors"], manifest["output_tensors"]
    return _array([len(tensors), len(operations), len(inputs), len(outputs), tensors,
                   operations, [*inputs, *([255] * (3 - len(inputs)))],
                   [*outputs, *([255] * (2 - len(outputs)))]])


def _plan_initializer(index, manifest):
    buffers = [[b["tensor"], 0 if b["space"] == "host" else 1, b["bytes"]]
               for b in manifest["buffers"]]
    events = [[{"bind_input": 0, "copy": 1, "execute": 2, "publish_output": 3}[e["kind"]],
               e["operation"] if e["operation"] is not None else 255,
               {None: 255, "c11": 0, "cuda-sm86": 1}[e["target"]],
               e["inputs"][0] if e["inputs"] else 255,
               e["inputs"][1] if len(e["inputs"]) == 2 else 255,
               e["outputs"][0] if e["outputs"] else 255] for e in manifest["events"]]
    return _array([index // 3, index % 3, len(buffers), len(events),
                   manifest["planned_buffer_bytes"], manifest["planned_copy_bytes"],
                   [0 if op["target"] == "c11" else 1 for op in manifest["operations"]],
                   buffers, events])


def _bindings(rows):
    return '\n'.join([
        '#include "abi.h"',
        "const struct tuc_graph tuc_graphs[TUC_GRAPH_COUNT] = {",
        ",\n".join(_graph_initializer(row[4]) for row in rows[::3]), "};",
        "const struct tuc_plan tuc_plans[TUC_PLAN_COUNT] = {",
        ",\n".join(_plan_initializer(i, row[4]) for i, row in enumerate(rows)), "};",
        "const char *const tuc_plan_digests[TUC_PLAN_COUNT] = {",
        ",\n".join('"' + _digest(row[3].manifest_json) + '"' for row in rows), "};", "",
    ])


def _corpora(rows):
    lines = ['#include "abi.h"']
    initializers = []
    for index, (family, shape, _, _, manifest) in enumerate(rows[::3]):
        groups = []
        for group, tensor_ids in (("inputs", manifest["input_tensors"]),
                                  ("outputs", manifest["output_tensors"])):
            vectors = []
            for vector in range(3):
                values = (oracle.fixed_inputs(shape, vector) if group == "inputs" else
                          oracle.reference_outputs(family, shape, vector))
                names = []
                for tensor in range(10):
                    if tensor not in tensor_ids:
                        names.append("NULL")
                        continue
                    name = f"tuc_{group}_{index}_{vector}_{tensor}"
                    bits = [oracle._bits(value) for value in
                            values[manifest["tensors"][tensor]["name"]]]
                    rendered = ",".join(f"UINT32_C(0x{value:08x})" for value in bits)
                    lines.append(f"static const uint32_t {name}[] = {{{rendered}}};")
                    names.append(name)
                vectors.append("{" + ",".join(names) + "}")
            groups.append("{" + ",".join(vectors) + "}")
        initializers.append("{" + ",".join(groups) + "}")
    return "\n".join([*lines, "const struct tuc_corpus tuc_corpora[TUC_GRAPH_COUNT] = {",
                       ",\n".join(initializers), "};", ""])


def _wrapper(graph, manifest, device):
    prefix = "cuda" if device else "op"
    lines = ['#include "../../abi.h"']
    if device:
        lines.insert(0, "#include <cuda_runtime.h>")
    for op in manifest["operations"]:
        symbol = op["cuda_symbol"] if device else op["symbol"]
        lines.append(f"#define {symbol} tuc_case_{graph}_{prefix}_{op['index']}")
    lines.append('#include "kernels.cuh"' if device else '#include "generated.c"')
    name = f"tuc_case_{graph}_{'device' if device else 'host'}"
    linkage = 'extern "C" ' if device else ""
    lines += [f"{linkage}bool {name}(uint32_t op, const float *a, const float *b, float *out) {{",
              "  (void)b;", "  switch (op) {"]
    for op in manifest["operations"]:
        symbol = f"tuc_case_{graph}_{prefix}_{op['index']}"
        args = "a, b, out" if op["kind"] == "matmul" else "a, out"
        launch = (f"<<<{op['launch']['blocks']}U,128U>>>" if device else "")
        lines.append(f"    case {op['index']}U: {symbol}{launch}({args}); break;")
    lines += ["    default: return false;", "  }"]
    lines += (["  return cudaGetLastError() == cudaSuccess &&",
               "         cudaDeviceSynchronize() == cudaSuccess;"]
              if device else ["  return true;"])
    return "\n".join([*lines, "}", ""])


def _dispatch(device):
    target = "device" if device else "host"
    linkage = 'extern "C" ' if device else ""
    params = "uint32_t op, const float *a, const float *b, float *out"
    lines = ['#include "abi.h"']
    lines += [f"{linkage}bool tuc_case_{i}_{target}({params});" for i in range(12)]
    lines += [f"{linkage}bool tuc_{target}_dispatch(uint32_t graph, {params}) {{",
              "  switch (graph) {"]
    lines += [f"    case {i}U: return tuc_case_{i}_{target}(op, a, b, out);" for i in range(12)]
    return "\n".join([*lines, "    default: return false;", "  }", "}", ""])


def artifact_files(rows=None):
    """Render the fixed portfolio; rows is an internal cache from bundles().

    This example has no external artifact/row ingestion API. CLI emission and
    acceptance always reconstruct rows from the validated repository portfolio.
    """
    rows = bundles() if rows is None else rows
    files = {name: _read(CONTEXT / name) for name in SUPPORT_FILES}
    files.update({"bindings.c": _bindings(rows), "corpora.c": _corpora(rows),
                  "dispatch_host.c": _dispatch(False), "dispatch_device.cu": _dispatch(True)})
    files["source-bindings.json"] = _json({name: _digest(_read(ROOT / name))
                                          for name in SOURCE_BINDINGS})
    for index, row in enumerate(rows):
        files[f"plans/{index:02d}.json"] = row[3].manifest_json
        if index % 3 == 0:
            graph = index // 3
            for name in ("generated.c", "generated.h", "kernels.cuh"):
                files[f"cases/{graph:02d}/{name}"] = row[3].files()[name]
            for device in (False, True):
                name = "device.cu" if device else "host.c"
                files[f"cases/{graph:02d}/{name}"] = _wrapper(graph, row[4], device)
    if (any(len(text.encode("utf-8")) > MAX_FILE_BYTES for text in files.values()) or
            sum(len(text.encode("utf-8")) for text in files.values()) > MAX_CONTEXT_BYTES):
        raise ValueError("native DAG artifact budget exceeded")
    return files


def _selection(index, worker):
    if (type(index) is not int or not 0 <= index < 36 or type(worker) is not str or
            worker not in ("c11", "matrix") or (worker == "c11" and index % 3 != 0)):
        raise ValueError("native DAG selector rejected")


def expected_receipt(index, worker, mode="execute", fault=0, rows=None):
    """Synthetic exact protocol expectation; never an execution observation."""
    _selection(index, worker)
    if type(mode) is not str or mode not in ("preflight", "execute"):
        raise ValueError("native DAG mode rejected")
    if (type(fault) is not int or not 0 <= fault <= 4 or
            (fault == 4 and index % 3 == 0) or (fault and mode != "execute")):
        raise ValueError("native DAG fault rejected")
    rows = bundles() if rows is None else rows
    manifest = rows[index][4]
    counts = dict.fromkeys(COUNTERS, 0)
    result = {"schema_version": SCHEMA, "worker": worker, "plan_index": index,
              "plan_digest": _digest(rows[index][3].manifest_json), "mode": mode,
              "status": "PASS", "reason": "none"}
    if mode == "preflight":
        return {**result, **counts}
    buffers = manifest["buffers"]
    for _ in range(6):
        ready = set()
        copied = published = 0
        for event in manifest["events"]:
            kind = event["kind"]
            if any(slot not in ready for slot in event["inputs"]):
                return {**result, "status": "ERROR", "reason": "missing_operand", **counts}
            if kind == "execute":
                if fault == 1 and event["operation"] == 0:
                    continue
                target = event["target"]
                counts["cpu_calls" if target == "c11" else "gpu_calls"] += 1
                if target != "c11":
                    counts["validation_download_calls"] += 1
                    counts["validation_download_bytes"] += buffers[event["outputs"][0]]["bytes"]
            elif kind == "copy":
                if fault == 4 and copied == 0:
                    copied += 1
                    continue
                copied += 1
                buffer = buffers[event["outputs"][0]]
                direction = "upload" if buffer["space"] == "accelerator" else "download"
                counts[direction + "_calls"] += 1
                counts[direction + "_bytes"] += buffer["bytes"]
            elif kind == "publish_output":
                if published == 0 and fault == 2:
                    return {**result, "status": "ERROR", "reason": "numeric_mismatch", **counts}
                if published == 0 and fault == 3:
                    published += 1
                    continue
                published += 1
                counts["published_outputs"] += 1
                counts["scalar_checks"] += buffers[event["inputs"][0]]["bytes"] // 4
            ready.update(event["outputs"])
        if fault == 3:
            return {**result, "status": "ERROR", "reason": "missing_publication", **counts}
        counts["case_runs"] += 1
    return {**result, **counts}


def invalid_receipt(worker):
    if type(worker) is not str or worker not in ("c11", "matrix"):
        raise ValueError("native DAG worker rejected")
    return {"schema_version": SCHEMA, "worker": worker, "plan_index": 255,
            "plan_digest": "none", "mode": "invalid", "status": "ERROR",
            "reason": "invalid_invocation", **dict.fromkeys(COUNTERS, 0)}


def expected_files(worker, rows=None):
    if type(worker) is not str or worker not in ("c11", "matrix"):
        raise ValueError("native DAG worker rejected")
    rows = bundles() if rows is None else rows
    result = {}
    for build in (("static", "sanitized") if worker == "c11" else ("matrix",)):
        for index in (range(0, 36, 3) if worker == "c11" else range(36)):
            for mode in ("preflight", "execute"):
                result[f"{build}-{index}-{mode}.json"] = expected_receipt(
                    index, worker, mode, rows=rows
                )
            for fault in range(1, 5 if index % 3 else 4):
                result[f"{build}-{index}-fault{fault}.json"] = expected_receipt(
                    index, worker, fault=fault, rows=rows
                )
        for selector in ("plan", "mode"):
            result[f"{build}-invalid-{selector}.json"] = invalid_receipt(worker)
    if worker == "c11":
        result["sanitized-contract.json"] = {
            "schema_version": "tuc.bounded_dag_native_contract.v0", "status": "PASS",
            "plans": 36, "mutation_checks": 194688,
        }
    return result


def _exact(value, expected):
    if (type(value) is not dict or set(value) != set(expected) or
            any(type(key) is not str for key in value) or
            any(type(value[key]) is not type(expected[key]) or value[key] != expected[key]
                for key in expected)):
        raise ValueError("native DAG observation rejected")
    return value


def report(rows=None, files=None):
    rows = bundles() if rows is None else rows
    files = artifact_files(rows) if files is None else files
    totals = dict.fromkeys(COUNTERS, 0)
    for index in range(36):
        expected = expected_receipt(index, "matrix", rows=rows)
        for key in COUNTERS:
            totals[key] += expected[key]
    return {"schema_version": "tuc.bounded_dag_native_candidate.v0", "status": "PASS",
            "graphs": 12, "plans": 36, "context_digest": _digest(_json(files)),
            "expected_matrix_counters": totals, "native_execution_observed": False,
            "cuda_execution_observed": False, "normal_runtime_admission": False,
            "latency_ns": None, "energy_pj": None}


def emit_context():
    files = artifact_files()
    parent = ROOT / "tmp"
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise ValueError("native DAG context parent rejected")
    parent.mkdir(exist_ok=True)
    if parent.resolve() != ROOT / "tmp":
        raise ValueError("native DAG context escapes workspace")
    directory = Path(tempfile.mkdtemp(prefix="bounded-dag-native.", dir=parent))
    for name, value in files.items():
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
    return directory


def accept(directory, worker):
    path = Path(directory)
    if (path.is_symlink() or not path.is_dir() or path.resolve().parent != ROOT / "tmp" or
            re.fullmatch(r"bounded-dag-native\.[A-Za-z0-9_-]{8,16}", path.name) is None):
        raise ValueError("native DAG evidence directory rejected")
    rows = bundles()
    files = artifact_files(rows)
    observations = {}
    expected = expected_files(worker, rows)
    for name in (*files, *expected):
        if any(parent.is_symlink() for parent in (path / name).parents if parent != ROOT):
            raise ValueError("native DAG evidence symlink rejected")
    for name, text in files.items():
        if _read(path / name) != text:
            raise ValueError("native DAG context drift rejected")
    for name, value in expected.items():
        observations[name] = _exact(oracle._receipt_json(_read(path / name, 4096)), value)
    images = {}
    for build in (("static", "sanitized") if worker == "c11" else ("matrix",)):
        image = _read(path / f"{build}-image-id.txt", 80).strip()
        if re.fullmatch(r"sha256:[0-9a-f]{64}", image) is None:
            raise ValueError("native DAG image identity rejected")
        images[build] = image
    result = {**report(rows, files), "schema_version": "tuc.bounded_dag_native_record.v0",
              "worker": worker, "native_execution_observed": True,
              "cuda_execution_observed": worker == "matrix", "image_ids": images,
              "observations": observations, "observation_scope": "fixed_portfolio_only"}
    if len(_json(result).encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("native DAG aggregate evidence budget exceeded")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--emit", action="store_true")
    action.add_argument("--accept", type=Path)
    parser.add_argument("--worker", choices=("c11", "matrix"))
    args = parser.parse_args()
    if bool(args.accept) != bool(args.worker):
        parser.error("--accept and --worker must be provided together")
    try:
        print(emit_context() if args.emit else
              _json(accept(args.accept, args.worker) if args.accept else report()))
    except (ValueError, OSError, UnicodeError) as error:
        print(f"native DAG rejected: {type(error).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
