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
| `@triton.jit` syntax | L0 | Preserved as a design goal; source text can pass execution-free preflight only, with no source-to-IR ingestion yet. |
| Triton source preflight | L0 | Bounded source syntax report rejects imports, decorator calls, dangerous builtins, host/device/network surfaces, unsupported calls, and HAC-IR leakage without producing a `ComputeGraph`; fuzz/property tests cover arbitrary decoded bytes and malicious seed cases. |
| Source Intent Intake | L1 | Schema-versioned plain-data intake builds `SourceIntentModule` from already decoded mappings; it rejects source text, preflight reports, unknown fields, and execution-surface keys. |
| Canonical Source Intent IR | L1 | Data-only frontend contract exists with deterministic dump and negative hardware-leakage tests; conversion is exposed only through a separate Source Intent Metadata adapter. |
| Source Intent Metadata Conversion | L2 | Execution-free adapter converts already constructed Source Intent IR to schema-versioned metadata, with source-intake, HAC-IR, runtime-plan, and compiler decision-report goldens. |
| Triton-like metadata adapter | L3 | Schema-versioned declarative metadata can be converted into `ComputeGraph`; intake, HAC-IR, runtime-plan, and decision-report goldens prove no source parsing or code execution. |
| Hardware-agnostic hints | L1 | Implemented as `CompilationHints` metadata. |
| MatMul | L3 | Lowered through TLIR -> HAC-IR -> HS-IR, covered by golden correctness fixtures, and included in Triton metadata frontend goldens. |
| Elementwise | L3 | Lowered and assigned to neutral `reference-cpu` fallback by default unless an explicit backend capability accepts it; ReLU reference fixture and Triton metadata frontend goldens cover semantics. |
| Reduction | L3 | Represented, supported by the linear simulator backend, covered by a sum-reduction fixture, and included in Triton metadata frontend goldens. |
| Softmax-like operation | L3 | Represented as an operation family and included in Triton metadata frontend goldens; decomposition is gated by the softmax operation-family planning contract. |
| GPU backend | L0 | Represented only when explicit backend capability data names a GPU backend; GPU is not the default fallback. |
| Photonic backend | L0 | Captured as roadmap target; simulator work comes later. |
| Neuromorphic backend | L0 | Captured as roadmap target; simulator work comes later. |

## Design Rules

- Hints must not change mathematical correctness.
- Frontend hints must not name hardware classes; use neutral intent such as
  `prefer_linear_accelerator`.
- Unsupported operations must remain visible and explainable.
- Fallback backend assignment must be explicit in HS-IR.
- Compatibility claims must be backed by tests or examples.
- Real Triton-facing intake must remain execution-free until a separate parser
  and sandbox RFC exists.
- Direct source parsing must satisfy
  [Triton Source Threat Model](TRITON_SOURCE_THREAT_MODEL.md) before moving
  beyond L0.
- Source-text preflight is documented in
  [Triton Source Preflight](TRITON_SOURCE_PREFLIGHT.md), but it is not source
  ingestion.
- Canonical Source Intent IR is documented in
  [Source Intent IR](SOURCE_INTENT_IR.md).
- Source Intent Intake is documented in
  [Source Intent Intake](SOURCE_INTENT_INTAKE.md). It accepts plain data, not
  source text or preflight reports.
- Source Intent Metadata Conversion is documented in
  [Source Intent Metadata Conversion](SOURCE_INTENT_METADATA.md). It starts
  from an already constructed `SourceIntentModule`, not source text.

## Next Step

Design source-text to Source Intent IR only after parser budgets, a semantic
mapping corpus, source-intent goldens, deterministic diagnostics, HAC-IR review
evidence, runtime-plan goldens, compiler decision-report goldens, and a
security review are accepted.
