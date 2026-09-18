"""An installed-package consumer of the bounded Source Intent compiler.

This script compiles metadata and source text only. It never invokes a native
toolchain, loads generated code, or observes CPU/CUDA execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from dataclasses import asdict
from pathlib import Path

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_source import (
    BoundedBackendBinding,
    BoundedSourceCompilation,
    compile_bounded_source_intent,
    validate_bounded_source_compilation,
)
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind

PROFILES = ("cpu", "gpu", "mixed")
MAX_REPORT_BYTES = 65536
_ALL_OPS = frozenset(
    {OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}
)
_PRIMITIVE_FILES = ("generated.c", "generated.h", "kernels.cuh")


def source_module() -> SourceIntentModule:
    """Two projections feed a third matmul; the raw left branch also returns."""

    return SourceIntentModule(
        name="project_recombine_and_summarize",
        tensors=tuple(
            SourceIntentTensor(name, shape)
            for name, shape in (
                ("a", (3, 2)),
                ("b", (2, 4)),
                ("c", (4, 3)),
                ("d", (3, 2)),
                ("p", (3, 4)),
                ("q", (4, 2)),
                ("rp", (3, 4)),
                ("rq", (4, 2)),
                ("joined", (3, 2)),
                ("raw_rows", (3,)),
                ("joint_rows", (3,)),
            )
        ),
        operations=(
            SourceIntentOperation("left_projection", "matmul", ("a", "b"), ("p",)),
            SourceIntentOperation("right_projection", "matmul", ("c", "d"), ("q",)),
            SourceIntentOperation(
                "left_activation", "elementwise", ("p",), ("rp",),
                attributes={"elementwise_kind": "relu"},
            ),
            SourceIntentOperation(
                "right_activation", "elementwise", ("q",), ("rq",),
                attributes={"elementwise_kind": "relu"},
            ),
            SourceIntentOperation("recombine", "matmul", ("rp", "rq"), ("joined",)),
            SourceIntentOperation(
                "left_rows", "reduction", ("p",), ("raw_rows",), attributes={"axis": 1},
            ),
            SourceIntentOperation(
                "joined_rows", "reduction", ("joined",), ("joint_rows",),
                attributes={"axis": 1},
            ),
        ),
        returns=(
            SourceIntentReturn("branch_total", "raw_rows"),
            SourceIntentReturn("joined_total", "joint_rows"),
        ),
    )


def backend_bindings(profile: str) -> tuple[BoundedBackendBinding, ...]:
    """Select capabilities; no operation names or placement overrides enter here."""

    if profile not in PROFILES:
        raise ValueError("unsupported consumer profile")
    cpu = BoundedBackendBinding(
        capability=BackendCapability(
            name="consumer_cpu",
            supported_ops=_ALL_OPS,
            preferred_for=(
                frozenset({OperationKind.ELEMENTWISE, OperationKind.REDUCTION})
                if profile == "mixed" else frozenset()
            ),
            memory_domain=MemoryDomainKind.HOST_RAM,
        ),
        target=DAGTarget.C11,
    )
    gpu = BoundedBackendBinding(
        capability=BackendCapability(
            name="consumer_gpu",
            supported_ops=(
                frozenset({OperationKind.MATMUL}) if profile == "mixed" else _ALL_OPS
            ),
            preferred_for=(
                frozenset({OperationKind.MATMUL}) if profile == "mixed" else frozenset()
            ),
            memory_domain=MemoryDomainKind.UNKNOWN,
        ),
        target=DAGTarget.CUDA_SM86,
    )
    return {"cpu": (cpu,), "gpu": (gpu,), "mixed": (cpu, gpu)}[profile]


def compile_profile(profile: str) -> BoundedSourceCompilation:
    module = source_module()
    bindings = backend_bindings(profile)
    result = compile_bounded_source_intent(module, bindings)
    validate_bounded_source_compilation(module, bindings, result)
    return result


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _common(result: BoundedSourceCompilation) -> dict[str, object]:
    manifest = json.loads(result.artifacts.manifest_json)
    files = result.artifacts.files()
    return {
        "source_intent_digest": result.source_intent_digest,
        "hac_ir_digest": manifest["hac_ir_digest"],
        "primitive_source_digests": {name: _sha256(files[name]) for name in _PRIMITIVE_FILES},
        "inputs": [asdict(binding) for binding in result.input_bindings],
        "returns": [asdict(binding) for binding in result.output_bindings],
        "tensors": manifest["tensors"],
        "operations": [
            {key: operation[key] for key in ("index", "name", "kind", "inputs", "outputs")}
            for operation in manifest["operations"]
        ],
    }


def build_report() -> dict[str, object]:
    """Expose identical computation and the three independently derived schedules."""

    common: dict[str, object] | None = None
    profiles = {}
    for profile in PROFILES:
        result = compile_profile(profile)
        profile_common = _common(result)
        if common is None:
            common = profile_common
        elif common != profile_common:
            raise ValueError("consumer computation changed across capability profiles")
        manifest = json.loads(result.artifacts.manifest_json)
        if manifest["native_execution_observed"] or manifest["normal_runtime_admission"]:
            raise ValueError("consumer requires emission-only artifacts")
        profiles[profile] = {
            "backend_bindings_digest": result.backend_bindings_digest,
            "capabilities": [
                {
                    "name": binding.capability.name,
                    "target": binding.target.value,
                    "supported_ops": sorted(op.value for op in binding.capability.supported_ops),
                    "preferred_for": sorted(op.value for op in binding.capability.preferred_for),
                }
                for binding in backend_bindings(profile)
            ],
            "assignments": [
                {
                    "operation": assignment.operation_name,
                    "backend": assignment.backend_name,
                    "reason": assignment.reason,
                }
                for assignment in result.compilation.partition_plan.assignments
            ],
            "targets": manifest["targets"],
            "buffers": manifest["buffers"],
            "events": manifest["events"],
            "planned_buffer_bytes": manifest["planned_buffer_bytes"],
            "planned_copy_bytes": manifest["planned_copy_bytes"],
            "schedule_digest": _sha256(result.artifacts.files()["schedule.h"]),
        }
    return {
        "schema_version": "bounded_source_consumer.v1",
        "graph": source_module().name,
        "computation": common,
        "profiles": profiles,
        "same_source_hac_primitives_and_returns": True,
        "native_execution_observed": False,
        "normal_runtime_admission": False,
    }


def report_text() -> str:
    text = json.dumps(build_report(), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    if len(text.encode("utf-8")) > MAX_REPORT_BYTES:
        raise ValueError("consumer report exceeds byte limit")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", type=Path, help="compare exact output with a bounded report file",
    )
    args = parser.parse_args(argv)
    try:
        text = report_text()
        if args.check is not None:
            if not stat.S_ISREG(args.check.lstat().st_mode):
                raise ValueError("expected report must be a regular file")
            with args.check.open("rb") as stream:
                expected = stream.read(MAX_REPORT_BYTES + 1)
            if expected != text.encode("utf-8"):
                raise ValueError("expected report differs")
    except (OSError, ValueError):
        print("bounded source consumer verification failed", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
