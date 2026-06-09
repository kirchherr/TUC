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
| `@triton.jit` syntax | L0 | Preserved as a design goal; no Python source parser yet. |
| Triton-like metadata adapter | L3 | Schema-versioned declarative metadata can be converted into `ComputeGraph`; intake, HAC-IR, runtime-plan, and decision-report goldens prove no source parsing or code execution. |
| Hardware-agnostic hints | L1 | Implemented as `CompilationHints` metadata. |
| MatMul | L3 | Lowered through TLIR -> HAC-IR -> HS-IR, covered by golden correctness fixtures, and included in Triton metadata frontend goldens. |
| Elementwise | L3 | Lowered and assigned to fallback backend by default; ReLU reference fixture and Triton metadata frontend goldens cover semantics. |
| Reduction | L3 | Represented, supported by the linear simulator backend, covered by a sum-reduction fixture, and included in Triton metadata frontend goldens. |
| Softmax-like operation | L3 | Represented as an operation family and included in Triton metadata frontend goldens; decomposition is gated by the softmax operation-family planning contract. |
| GPU backend | L0 | Represented as fallback backend name only. |
| Photonic backend | L0 | Captured as roadmap target; simulator work comes later. |
| Neuromorphic backend | L0 | Captured as roadmap target; simulator work comes later. |

## Design Rules

- Hints must not change mathematical correctness.
- Unsupported operations must remain visible and explainable.
- Fallback backend assignment must be explicit in HS-IR.
- Compatibility claims must be backed by tests or examples.
- Real Triton-facing intake must remain execution-free until a separate parser
  and sandbox RFC exists.

## Next Step

Use the schema-versioned Triton metadata intake contract as the entry point for
future Triton idiom coverage before any source parser or `@triton.jit` handling
is accepted.
