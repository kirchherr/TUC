# Triton Compatibility

TUC starts by preserving Triton-style intent, not by claiming full Triton
compatibility on day one.

## Compatibility Levels

| Level | Meaning |
| --- | --- |
| L0 Conceptual | TUC can represent the operation family and metadata. |
| L1 Prototype | TUC can lower the operation through TLIR, HAC-IR, and HS-IR. |
| L2 Correctness | TUC has golden tests against a reference implementation. |
| L3 Triton Adapter | TUC can ingest a Triton-like frontend representation. |
| L4 Backend Parity | TUC can execute through a real backend with acceptable correctness and performance. |

## Current Matrix

| Feature | Level | Notes |
| --- | --- | --- |
| `@triton.jit` syntax | L0 | Preserved as a design goal; no parser or adapter yet. |
| Hardware-agnostic hints | L1 | Implemented as `CompilationHints` metadata. |
| MatMul | L1 | Lowered through TLIR -> HAC-IR -> HS-IR. |
| Elementwise | L1 | Lowered and assigned to fallback backend by default. |
| Reduction | L1 | Represented and supported by the linear simulator backend. |
| Softmax-like operation | L1 | Represented as an operation family; decomposition is future work. |
| GPU backend | L0 | Represented as fallback backend name only. |
| Photonic backend | L0 | Captured as roadmap target; simulator work comes later. |
| Neuromorphic backend | L0 | Captured as roadmap target; simulator work comes later. |

## Design Rules

- Hints must not change mathematical correctness.
- Unsupported operations must remain visible and explainable.
- Fallback backend assignment must be explicit in HS-IR.
- Compatibility claims must be backed by tests or examples.

## Next Step

Move MatMul and Elementwise from L1 to L2 by adding golden correctness tests.
