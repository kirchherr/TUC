"""Inert checked C11 graph entrypoints from revalidated public compilations.

This is source generation, not a native executor, loader or runtime admission.
The original primitive artifact bytes and their numerical contract are unchanged.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import prod
from typing import cast

from tuc.backends.bounded_c11_codegen import (
    C11GraphSpec,
    C11OperationSpec,
    emit_checked_graph,
    validate_spec,
)
from tuc.compiler.bounded_source import (
    BoundedBackendBinding,
    BoundedSourceCompilation,
    compile_bounded_source_intent,
    validate_bounded_source_compilation,
)
from tuc.frontend.source_intent import SourceIntentModule

MAX_C11_ENTRYPOINT_BYTES = 262144
MAX_C11_MANIFEST_BYTES = 65536
SCHEMA_VERSION = "tuc.bounded_c11_entrypoint.v0"


@dataclass(frozen=True)
class BoundedC11Entrypoint:
    """Three deterministic text files and their graph-specific exported symbol."""

    header: str
    source: str
    manifest_json: str
    entrypoint_symbol: str

    def files(self) -> dict[str, str]:
        """Return a fresh mapping; the artifact itself grants no execution rights."""
        state = _artifact_state(self)
        return {"entrypoint.h": state["header"], "entrypoint.c": state["source"],
                "entrypoint.json": state["manifest_json"]}


def _artifact_state(value: object) -> dict[str, str]:
    if type(value) is not BoundedC11Entrypoint:
        raise ValueError("bounded C11 artifact rejected")
    state = object.__getattribute__(value, "__dict__")
    keys = {"header", "source", "manifest_json", "entrypoint_symbol"}
    if (type(state) is not dict or len(state) != len(keys) or
            any(type(key) is not str or len(key) > 32 for key in state) or set(state) != keys):
        raise ValueError("bounded C11 artifact rejected")
    total = 0
    for key, text in state.items():
        limit = (MAX_C11_MANIFEST_BYTES if key == "manifest_json" else
                 76 if key == "entrypoint_symbol" else MAX_C11_ENTRYPOINT_BYTES)
        if type(text) is not str or len(text) > limit:
            raise ValueError("bounded C11 artifact rejected")
        try:
            size = len(text.encode("utf-8"))
        except UnicodeError as error:
            raise ValueError("bounded C11 artifact rejected") from error
        if size > limit:
            raise ValueError("bounded C11 artifact rejected")
        total += size
    if total > MAX_C11_ENTRYPOINT_BYTES:
        raise ValueError("bounded C11 artifact budget rejected")
    return cast(dict[str, str], state)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def emit_bounded_c11_entrypoint(
    module: SourceIntentModule,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    compilation: BoundedSourceCompilation,
) -> BoundedC11Entrypoint:
    """Revalidate all original data, then emit a CPU-only checked graph wrapper.

    The caller's mutable compiler metadata is never interpreted after validation:
    emission consumes an independent fresh reconstruction. An unused valid CUDA
    binding remains part of provenance, but any selected CUDA operation rejects.
    C callers must provide live, stable descriptor arrays and buffers; a returned
    error preserves all output values under these caller preconditions.
    """
    validate_bounded_source_compilation(module, backend_bindings, compilation)
    fresh = compile_bounded_source_intent(module, backend_bindings)
    original = json.loads(fresh.artifacts.manifest_json)
    if (any(op["target"] != "c11" for op in original["operations"]) or
            any(buffer["space"] != "host" for buffer in original["buffers"]) or
            any(event["kind"] == "copy" for event in original["events"])):
        raise ValueError("bounded C11 entrypoint requires selected CPU operations")
    spec = C11GraphSpec(
        tuple(tuple(tensor["shape"]) for tensor in original["tensors"]),
        tuple(C11OperationSpec(op["kind"], tuple(op["inputs"]), op["outputs"][0])
              for op in original["operations"]),
        tuple(binding.tensor_index for binding in fresh.input_bindings),
        tuple(binding.tensor_index for binding in fresh.output_bindings),
    )
    scratch, work = validate_spec(spec)
    abi = {
        "version": "tuc.c11.buffer_abi.v0",
        "platform": "linux-x86_64-sse2-flat-address",
        "input_descriptor": "struct tuc_c11_input { const float *data; size_t elements; }",
        "output_descriptor": "struct tuc_c11_output { float *data; size_t elements; }",
        "statuses": {"TUC_C11_OK": 0, "TUC_C11_ARGUMENT": 1, "TUC_C11_NUMERIC": 2,
                     "TUC_C11_ENVIRONMENT": 3},
        "exact_counts_and_extents": True,
        "all_buffer_pairs_disjoint": True,
        "buffers_disjoint_from_descriptor_arrays": True,
        "descriptor_arrays_disjoint": True,
        "descriptor_snapshot_before_payload_reads": True,
        "caller_preconditions": ["live readable input and descriptor storage",
                                 "live writable output storage",
                                 "actual allocation extents cover all declared extents",
                                 "no concurrent mutation of buffers or descriptors"],
        "outputs_unchanged_on_returned_error": True,
        "publication_is_concurrent_transaction": False,
        "pointer_liveness_proved": False,
    }
    numeric = {
        "dtype": "binary32",
        "rounding": "FE_TONEAREST",
        "mxcsr_clear_mask": "0xe040",
        "mxcsr_required_exception_masks": "0x1f80",
        "accepted_values": "normal-or-signed-zero",
        "classification": "memcpy-uint32-exponent-bits",
        "every_rounded_product_and_sequential_sum_checked": True,
        "nonzero_operands_product_rounding_to_zero_rejected": True,
        "exact_zero_products_and_exact_cancellation_allowed": True,
        "fma_and_reassociation": False,
        "floating_point_exception_flags_preserved": False,
        "required_build_flags": ["-std=c11", "-fno-fast-math", "-ffp-contract=off",
                                 "-frounding-math"],
    }
    if any(op.kind in ("add", "add_row_bias") for op in spec.operations):
        numeric["addition"] = "one_checked_binary32_addition_per_output_element"
        numeric["broadcast"] = "equal_shapes_or_rank2_lhs_with_rank1_rhs_row_bias_only"
    provenance = {
        "schema_version": SCHEMA_VERSION,
        "source_intent_digest": fresh.source_intent_digest,
        "backend_bindings_digest": fresh.backend_bindings_digest,
        "hac_ir_digest": original["hac_ir_digest"],
        "original_artifacts_digest": _digest(_json(fresh.artifacts.files())),
        "inputs": [asdict(binding) for binding in fresh.input_bindings],
        "outputs": [asdict(binding) for binding in fresh.output_bindings],
        "graph": asdict(spec),
        "abi": abi,
        "numeric_policy": numeric,
    }
    binding_digest = _digest(_json(provenance))
    header, source, symbol = emit_checked_graph(spec, binding_digest)
    manifest = {
        **provenance,
        "binding_digest": binding_digest,
        "entrypoint_symbol": symbol,
        "tensors": [{"index": i, "shape": shape, "elements": prod(shape),
                     "bytes": prod(shape) * 4} for i, shape in enumerate(spec.tensor_shapes)],
        "operations": [asdict(op) for op in spec.operations],
        "scratch_bytes": scratch,
        "scratch_bytes_scope": "tensor-payload-only; bounded stack bookkeeping is additional",
        "scalar_work": work,
        "source_digests": {"entrypoint.h": _digest(header), "entrypoint.c": _digest(source)},
        "native_execution_observed": False,
        "normal_runtime_admission": False,
        "latency_ns": None,
        "energy_pj": None,
        "blocked_claims": ["native correctness", "native execution", "runtime admission",
                           "pointer liveness", "concurrent atomic publication", "performance"],
    }
    artifact = BoundedC11Entrypoint(header, source, _json(manifest), symbol)
    _artifact_state(artifact)
    return artifact


def validate_bounded_c11_entrypoint(
    module: SourceIntentModule,
    backend_bindings: tuple[BoundedBackendBinding, ...],
    compilation: BoundedSourceCompilation,
    artifact: BoundedC11Entrypoint,
) -> None:
    """Compare bounded exact text against a complete trusted reconstruction."""
    state = _artifact_state(artifact)
    expected = _artifact_state(emit_bounded_c11_entrypoint(module, backend_bindings, compilation))
    for key, text in expected.items():
        if len(state[key]) != len(text) or state[key] != text:
            raise ValueError("bounded C11 artifact differs from source compilation")


__all__ = ["BoundedC11Entrypoint", "emit_bounded_c11_entrypoint",
           "validate_bounded_c11_entrypoint"]
