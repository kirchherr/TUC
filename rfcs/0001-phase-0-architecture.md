# RFC 0001: Phase 0 Architecture

## Status

Accepted for prototype implementation

## Summary

Phase 0 starts with a Python-level prototype that models TUC's major contracts:
developer hints, a hardware-agnostic compute graph, backend capabilities,
backend lowering, and runtime partitioning.

## Motivation

TUC's long-term goal is a native compiler and runtime stack. Before building a
deep MLIR pipeline, the project needs a small implementation that makes core
contracts testable and understandable.

## Goals

- Create a real package structure under `src/tuc`.
- Represent hardware-agnostic compute intent.
- Carry developer hints as metadata.
- Let backends declare capabilities.
- Partition operations by backend capability.
- Lower a supported subgraph through a simulator backend.
- Keep the implementation small enough to rewrite when native MLIR work begins.

## Non-Goals

- Full Triton compatibility.
- Native MLIR dialects.
- CUDA, HIP, photonic, or neuromorphic production backends.
- PyTorch graph capture.
- Performance optimization.

## Proposal

Implement the following prototype modules:

- `tuc.frontend.hints`
- `tuc.ir.model`
- `tuc.backends.base`
- `tuc.backends.simulator`
- `tuc.runtime.partitioning`

The simulator backend accepts matmul and reduction operations. The runtime
partitioner prefers backend-declared preferred operations and falls back to a
default backend for unsupported operations.

## Compatibility

No public compatibility is promised in Phase 0.

## Testing

Add unit tests for:

- Hint metadata serialization.
- Invalid error budgets.
- Simulator backend lowering.
- Unsupported backend operations.
- Runtime partitioning and fallback.

## Open Questions

- Which final open-source license should TUC use?
- When should the project move from Python IR to native MLIR dialects?
- Which Triton integration path should be attempted first?
