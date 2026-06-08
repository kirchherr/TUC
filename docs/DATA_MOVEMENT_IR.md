# Data Movement Aware IR

TUC treats data movement as a first-class compiler fact. This is necessary
because future accelerators may keep increasing arithmetic throughput while
system performance is still constrained by memory bandwidth, placement,
transfer latency, layout conversion, and synchronization.

The early Python IR model is intentionally small, but it establishes the
boundary that later MLIR dialect work must preserve.

## Why This Exists

The von Neumann bottleneck is not only a hardware issue. A compiler that sees
only operations can select an accelerator that is fast for arithmetic but slow
or unsafe once transfers, buffers, and layouts are considered.

TUC therefore records movement facts alongside compute facts:

- How many bytes an operation reads and writes.
- How many arithmetic operations are expected.
- The operation arithmetic intensity.
- The preferred memory domain.
- The layout constraint that downstream passes must respect.
- A graph-level movement summary for runtime planning.

## IR Placement

Current Phase 1 behavior:

- TLIR preserves Triton-like compute intent and developer hints.
- HAC-IR attaches movement estimates after MVP operation validation.
- HS-IR carries the same operation attributes plus backend assignments.
- HS-IR graph metadata includes a movement summary for runtime decisions.
- Partition plans include explicit runtime transfer edges and layout conversion
  costs.

This keeps the model inspectable without introducing hidden optimizer state.

## Current Model

The first model lives in `tuc.ir.memory` and `tuc.compiler.movement`.

Core types:

- `MemoryDomainKind`: host RAM, GPU HBM, device SRAM, analog weight banks,
  neuromorphic arrays, persistent memory, stream buffers, and unknown domains.
- `MemoryDomain`: a named memory domain with optional bandwidth, latency,
  energy, and capacity hints.
- `TransferEdge`: declarative transfer cost between memory domains.
- `LayoutConstraint`: row-major, column-major, blocked, vector, or unknown
  layout constraints.
- `MovementEstimate`: bytes read, bytes written, arithmetic operations,
  arithmetic intensity, preferred memory domain, layout, and notes.

Supported estimator coverage:

- `matmul`: rank-2 MVP matmul with exact output shape validation.
- `elementwise`: exact-shape elementwise operations.
- `reduction`: output element count must not exceed input element count.
- `softmax`: exact input/output shape, approximate arithmetic count.

Softmax movement estimates are planning evidence only. The operation-family
contract in [`SOFTMAX_OPERATION_PLANNING.md`](SOFTMAX_OPERATION_PLANNING.md)
defines the proof gate before accepting softmax proof graphs, runtime
decomposition, or softmax-specific candidate score components.

## Security Rules

Movement metadata is declarative data, not executable behavior.

- Unknown dtypes are rejected.
- Invalid shapes are rejected before estimates are attached.
- Tensor rank, element count, tensor count, and byte size have explicit
  estimator limits.
- Existing user-supplied `tuc.*` movement attributes are overwritten by the
  compiler pass rather than trusted.
- Missing movement attributes fail closed when summaries are requested.
- Backend claims must remain validated data. Capability checks must not execute
  plugin code or arbitrary host subprocesses.

These rules are part of the compiler attack-surface reduction strategy.

## Future Work

The next increments should be:

1. Attach validated backend memory-domain capabilities.
2. Let partitioning consider movement summary and operation intensity.
3. Add schema-versioned backend manifest files.
4. Add calibrated backend transfer-cost profile files.
5. Add fuzz tests for serialized IR and malicious backend capability metadata.
