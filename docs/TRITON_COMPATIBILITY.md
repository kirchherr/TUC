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
| `@triton.jit` syntax | L1 | Preserved as a design goal; source text can pass execution-free preflight, and one explicit research parser slice accepts a tiny subset without executing decorators or JIT. General syntax support remains blocked. |
| Triton source preflight | L0 | Bounded source syntax report rejects imports, decorator calls, dangerous builtins, host/device/network surfaces, unsupported calls, and HAC-IR leakage without producing a `ComputeGraph`; fuzz/property tests cover arbitrary decoded bytes and malicious seed cases. |
| Source Intent Intake | L1 | Schema-versioned plain-data intake builds `SourceIntentModule` from already decoded mappings; it rejects source text, preflight reports, unknown fields, and execution-surface keys. |
| Source Intent JSON Schema | L1 | Machine-readable `source_intent.v0` schema documents the plain-data contract for external frontend authors while runtime validation remains in Source Intent Intake. |
| Canonical Source Intent IR | L1 | Data-only frontend contract exists with deterministic dump and negative hardware-leakage tests; conversion is exposed only through a separate Source Intent Metadata adapter. |
| Source Intent Metadata Conversion | L2 | Execution-free adapter converts already constructed Source Intent IR to schema-versioned metadata, with source-intake, HAC-IR, runtime-plan, and compiler decision-report goldens. |
| Source Intent Frontend Conformance | L2 | In-memory conformance fixtures certify external frontend plain-data output through intake, optional public return semantics, metadata conversion, graph construction, return-alias preservation, and neutral planning while rejected cases fail closed at intake; report artifacts have a JSON Schema. |
| Source-To-Intent Parser Gate | L0 | Default parser intake remains blocked, while the required RFC, budgets, corpus, diagnostics, goldens, neutrality review, and conformance evidence are defined for broader parser work. |
| Source-To-Intent Readiness Report | L0 | Default parser intake remains blocked, while deterministic research readiness evidence now shows the proposal evidence set is complete. |
| Source-To-Intent Research Parser | L1 | Explicit-only parser slice converts a tiny caller-provided Triton-like source subset into validated `source_intent.v0` plain data with metadata-only report evidence and no compiler artifacts. |
| Source-To-Intent Parser Block Gate | L0 | CI-facing gate asserts the default source-to-intent parser path remains blocked and all required parser-readiness evidence is missing. |
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
- Real Triton-facing intake must remain execution-free; broader parser work
  requires separate review and sandbox evidence.
- General source parsing must satisfy
  [Triton Source Threat Model](TRITON_SOURCE_THREAT_MODEL.md) before moving
  beyond the explicit research slice.
- Source-text preflight is documented in
  [Triton Source Preflight](TRITON_SOURCE_PREFLIGHT.md), but it is not source
  ingestion.
- Canonical Source Intent IR is documented in
  [Source Intent IR](SOURCE_INTENT_IR.md).
- Source Intent Intake is documented in
  [Source Intent Intake](SOURCE_INTENT_INTAKE.md). It accepts plain data, not
  source text or preflight reports.
- Source Intent JSON Schema is documented in
  [Source Intent JSON Schema](SOURCE_INTENT_SCHEMA.md).
- Source Intent Metadata Conversion is documented in
  [Source Intent Metadata Conversion](SOURCE_INTENT_METADATA.md). It starts
  from an already constructed `SourceIntentModule`, not source text.
- Source Intent Frontend Conformance is documented in
  [Source Intent Frontend Conformance](SOURCE_INTENT_FRONTEND_CONFORMANCE.md).
  It checks in-memory plain-data cases and does not load frontend packages,
  parse source text, discover plugins, or execute backend artifacts.
- Source Intent Frontend Conformance reports use the schema documented in
  [Source Intent Frontend Conformance Report Schema](SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA.md).
  The schema covers report artifacts, not frontend payload semantics.
- Source-To-Intent Parser Gate is documented in
  [Source-To-Intent Parser Gate](SOURCE_TO_INTENT_PARSER_GATE.md). It keeps
  default parser intake blocked and governs broader parser work so source text
  cannot bypass intake, conformance, metadata conversion, HAC-IR neutrality
  review, runtime-plan goldens, or decision-report goldens.
- Source-To-Intent Readiness Report is documented in
  [Source-To-Intent Readiness Report](SOURCE_TO_INTENT_READINESS.md). It is a
  review artifact for parser proposals, not a source parser or ingestion path.
- Source-To-Intent Parser Block Gate is documented in
  [Source-To-Intent Parser Block Gate](SOURCE_TO_INTENT_PARSER_BLOCK_GATE.md).
  It keeps the default source-to-intent parser path closed in CI.
- Source-To-Intent Research Parser is documented in
  [Source-To-Intent Research Parser](SOURCE_TO_INTENT_RESEARCH_PARSER.md). It
  emits only `source_intent.v0` plain data for a tiny explicit subset and does
  not produce metadata, `ComputeGraph`, IR, runtime plans, or backend
  decisions.

## Next Step

Expand source-text to Source Intent IR only by adding parser budgets, semantic
mapping corpus cases, source-intent goldens, deterministic diagnostics, HAC-IR
review evidence, runtime-plan goldens, compiler decision-report goldens, and
security review evidence for the new syntax. External frontend proposals should
first publish a Source Intent Frontend Conformance report.
