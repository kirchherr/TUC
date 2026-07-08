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
| Triton Integration Readiness | L0 | Data-only readiness report for the Real Triton Integration milestone; it records satisfied and missing prerequisites while direct source ingestion and `@triton.jit` execution remain blocked. Schema: `schemas/triton_integration_readiness_report.v0.schema.json`; example: `examples/triton_integration_readiness.py`. |
| Real Triton Integration Admission Gate | L0 | Fail-closed admission report binding readiness, external frontend conformance, and the real integration threat model by digest while source ingestion, package import, plugin discovery, JIT, device access, generated artifacts, and native backend execution remain blocked. Schema: `schemas/real_triton_integration_admission_gate_report.v0.schema.json`; example: `examples/real_triton_integration_admission_gate.py`; docs: `docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md`, `docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md`. |
| Source Ingestion Quarantine Gate | L0 | First dedicated Real Triton Integration surface gate for `direct_source_ingestion`; it binds admission, parser-gate, preflight, and threat-model evidence by digest while source-to-ComputeGraph, source-to-HAC-IR, source-to-runtime-plan, import, JIT, and generated-artifact execution remain blocked. Schema: `schemas/source_ingestion_quarantine_gate_report.v0.schema.json`; example: `examples/source_ingestion_quarantine_gate.py`; doc: `docs/SOURCE_INGESTION_QUARANTINE_GATE.md`. |
| Package Import Sandbox Gate | L0 | Dedicated Real Triton Integration surface gate for `frontend_package_import`; it binds admission, external frontend conformance, source-ingestion quarantine, and sandbox-model evidence by digest while Python import, package code execution, entrypoint discovery, network, filesystem, environment, subprocess, dynamic-library, plugin discovery, and Source Intent from import remain blocked. Schema: `schemas/package_import_sandbox_gate_report.v0.schema.json`; example: `examples/package_import_sandbox_gate.py`; doc: `docs/PACKAGE_IMPORT_SANDBOX_GATE.md`. |
| Plugin Discovery Allowlist Gate | L0 | Dedicated Real Triton Integration surface gate for `plugin_discovery`; it binds admission, external frontend conformance, package-import sandbox, and allowlist-model evidence by digest while plugin discovery, entrypoint discovery, registry scans, filesystem scans, frontend package import, Python import, plugin code execution, network, subprocess, dynamic-library, device access, and capability claims from code remain blocked. Schema: `schemas/plugin_discovery_allowlist_gate_report.v0.schema.json`; example: `examples/plugin_discovery_allowlist_gate.py`; doc: `docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md`. |
| Triton JIT Execution Sandbox Gate | L0 | Dedicated Real Triton Integration surface gate for `triton_jit_execution`; it binds admission, source-ingestion quarantine, package-import sandbox, plugin-discovery allowlist, and sandbox-model evidence by digest while Triton JIT, kernel launch, generated artifact execution, device access, kernel-cache access, backend binary emission, package import, Python import, plugin discovery, network, subprocess, and dynamic-library surfaces remain blocked. Schema: `schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json`; example: `examples/triton_jit_execution_sandbox_gate.py`; doc: `docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md`. |
| Device Access Sandbox Gate | L0 | Dedicated Real Triton Integration surface gate for `device_access`; it binds admission, Triton-JIT sandbox, and device sandbox-model evidence by digest while device discovery, enumeration, driver calls, device handles, device memory allocation, memory mapping, direct memory access, kernel launch, generated artifact execution, subprocess, and dynamic-library surfaces remain blocked. Schema: `schemas/device_access_sandbox_gate_report.v0.schema.json`; example: `examples/device_access_sandbox_gate.py`; doc: `docs/DEVICE_ACCESS_SANDBOX_GATE.md`. |
| Generated Artifact Quarantine Gate | L0 | Dedicated Real Triton Integration surface gate for `generated_artifact_execution`; it binds admission, Triton-JIT sandbox, device-access sandbox, and quarantine-model evidence by digest while artifact emission, writes, loads, executable permissions, artifact-cache access, backend binary emission, generated artifact execution, device access, kernel launch, subprocess, and dynamic-library surfaces remain blocked. Schema: `schemas/generated_artifact_quarantine_gate_report.v0.schema.json`; example: `examples/generated_artifact_quarantine_gate.py`; doc: `docs/GENERATED_ARTIFACT_QUARANTINE_GATE.md`. |
| Native Backend Execution Security Gate | L0 | Dedicated Real Triton Integration surface gate for `native_backend_execution`; it binds admission, generated-artifact quarantine, device-access sandbox, backend plugin lifecycle policy, and security-model evidence by digest while native backend execution, native plugin ABI loading, backend plugin execution, symbol resolution, FFI calls, unsafe memory access, dynamic-library loading, generated artifact execution, device access, kernel launch, and subprocess surfaces remain blocked. Schema: `schemas/native_backend_execution_security_gate_report.v0.schema.json`; example: `examples/native_backend_execution_security_gate.py`; doc: `docs/NATIVE_BACKEND_EXECUTION_SECURITY_GATE.md`. |
| Real Triton Surface Gate Completion | L0 | Compact data-only review artifact binding admission and all seven dedicated surface gates by digest; it proves the surface-gate set is complete while Real Triton admission remains blocked and all surface gates remain non-admitting. Schema: `schemas/real_triton_surface_gate_completion_report.v0.schema.json`; example: `examples/real_triton_surface_gate_completion.py`; doc: `docs/REAL_TRITON_SURFACE_GATE_COMPLETION.md`. |
| Source-To-Intent Next Syntax Slice | L1 | Branched dataflow, fanout reuse, all current MVP operation families, and multiple public returns are bound by source-free semantic mapping evidence. Schema: `schemas/source_to_intent_next_syntax_report.v0.schema.json`; example: `examples/source_to_intent_next_syntax_slice.py`. |
| External Frontend Package Conformance | L1 | External frontend packages are reviewed as data-only manifests plus digest-only Source Intent fixtures, without package import, plugin discovery, direct source ingestion, or JIT execution. Schema: `schemas/external_frontend_package_conformance_report.v0.schema.json`; example: `examples/external_frontend_package_conformance.py`. |
| Source Intent Intake | L1 | Schema-versioned plain-data intake builds `SourceIntentModule` from already decoded mappings; it rejects source text, preflight reports, unknown fields, and execution-surface keys. |
| Source Intent JSON Schema | L1 | Machine-readable `source_intent.v0` schema documents the plain-data contract for external frontend authors while runtime validation remains in Source Intent Intake. |
| Source Intent Axis Attributes | L2 | Neutral `attributes.axis` semantics for `softmax` and `reduction` pass through Source Intent Intake, Metadata Conversion, and parser conformance evidence without backend/device facts. |
| Canonical Source Intent IR | L1 | Data-only frontend contract exists with deterministic dump and negative hardware-leakage tests; conversion is exposed only through a separate Source Intent Metadata adapter. |
| Source Intent Metadata Conversion | L2 | Execution-free adapter converts already constructed Source Intent IR to schema-versioned metadata, with source-intake, HAC-IR, runtime-plan, and compiler decision-report goldens. |
| Source Intent Frontend Conformance | L2 | In-memory conformance fixtures certify external frontend plain-data output through intake, optional public return semantics, metadata conversion, graph construction, return-alias preservation, and neutral planning while rejected cases fail closed at intake; report artifacts have a JSON Schema. |
| Source-To-Intent Parser Gate | L0 | Default parser intake remains blocked, while the required RFC, budgets, corpus, diagnostics, goldens, neutrality review, and conformance evidence are defined for broader parser work. |
| Source-To-Intent Readiness Report | L0 | Default parser intake remains blocked, while deterministic research readiness evidence now shows the proposal evidence set is complete. |
| Source-To-Intent Research Parser | L1 | Explicit-only parser slice converts a tiny caller-provided Triton-like source subset into validated `source_intent.v0` plain data with metadata-only report evidence and no compiler artifacts. |
| Source-To-Intent Research Parser Conformance Gate | L2 | Binds the `matmul -> elementwise` parser output slice to Source Intent Frontend Conformance while keeping default parser intake blocked. |
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
- Real Triton Integration Admission is documented in
  [Real Triton Integration Admission Gate](REAL_TRITON_INTEGRATION_ADMISSION_GATE.md)
  and [Real Triton Integration Threat Model](REAL_TRITON_INTEGRATION_THREAT_MODEL.md).
  It is an admission blocker, not permission to execute source, imports,
  plugins, JIT, devices, generated artifacts, or native backends.
- Source Ingestion Quarantine is documented in
  [Source Ingestion Quarantine Gate](SOURCE_INGESTION_QUARANTINE_GATE.md).
  It establishes the quarantine boundary for source buffers while keeping
  direct source ingestion and source-to-compiler-artifact paths blocked.
- Package Import Sandbox is documented in
  [Package Import Sandbox Gate](PACKAGE_IMPORT_SANDBOX_GATE.md). It establishes
  sandbox requirements for package-shaped frontend integration while keeping
  actual package import, Python import, and package code execution blocked.
- Plugin Discovery Allowlist is documented in
  [Plugin Discovery Allowlist Gate](PLUGIN_DISCOVERY_ALLOWLIST_GATE.md). It
  establishes allowlist requirements for plugin-shaped frontend integration
  while keeping actual plugin discovery, entrypoint discovery, registry scans,
  filesystem scans, and plugin code execution blocked.
- Triton JIT Execution Sandbox is documented in
  [Triton JIT Execution Sandbox Gate](TRITON_JIT_EXECUTION_SANDBOX_GATE.md). It
  establishes sandbox requirements for future JIT integration while keeping
  actual Triton JIT execution, kernel launch, cache access, device access, and
  executable artifacts blocked.
- Device Access Sandbox is documented in
  [Device Access Sandbox Gate](DEVICE_ACCESS_SANDBOX_GATE.md). It establishes
  sandbox requirements for future device integration while keeping actual
  device discovery, driver calls, device memory, direct memory access, and
  device handles blocked.
- Generated Artifact Quarantine is documented in
  [Generated Artifact Quarantine Gate](GENERATED_ARTIFACT_QUARANTINE_GATE.md).
  It establishes quarantine requirements for future generated artifacts while
  keeping artifact emission, artifact writes, executable permissions, and
  generated artifact execution blocked.
- Native Backend Execution Security is documented in
  [Native Backend Execution Security Gate](NATIVE_BACKEND_EXECUTION_SECURITY_GATE.md).
  It establishes security requirements for future native backend execution
  while keeping native backend loading, native plugin ABI loading, backend
  plugin execution, symbol resolution, FFI calls, unsafe memory access, devices,
  kernels, subprocesses, and generated artifacts blocked.
- Real Triton Surface Gate Completion is documented in
  [Real Triton Surface Gate Completion](REAL_TRITON_SURFACE_GATE_COMPLETION.md).
  It binds all seven dedicated surface gates by digest while keeping Real
  Triton admission blocked.
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
- Source Intent Axis Attributes are documented in
  [Source Intent Axis Attributes](SOURCE_INTENT_AXIS_ATTRIBUTES.md).
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
- Source-To-Intent Research Parser Conformance Gate is documented in
  [Source-To-Intent Research Parser Conformance Gate](SOURCE_TO_INTENT_RESEARCH_PARSER_CONFORMANCE_GATE.md).
  It proves the first parser output slice passes the reusable Source Intent
  Frontend Conformance path.

## Next Step

Use [Triton Integration Readiness](TRITON_INTEGRATION_READINESS.md) before
treating Real Triton Integration as roadmap progress. The current report at
`examples/triton_integration_readiness.py` is now `ready` as data-only review
evidence and is validated by
`schemas/triton_integration_readiness_report.v0.schema.json`.

Then use [Real Triton Integration Admission Gate](REAL_TRITON_INTEGRATION_ADMISSION_GATE.md)
with [Real Triton Integration Threat Model](REAL_TRITON_INTEGRATION_THREAT_MODEL.md).
The current gate at `examples/real_triton_integration_admission_gate.py` is
validated by `schemas/real_triton_integration_admission_gate_report.v0.schema.json`,
binds readiness and external frontend conformance by digest, and keeps real
admission blocked until dedicated surface gates exist.

The first dedicated surface gate is
[Source Ingestion Quarantine Gate](SOURCE_INGESTION_QUARANTINE_GATE.md). The
current report at `examples/source_ingestion_quarantine_gate.py` is validated by
`schemas/source_ingestion_quarantine_gate_report.v0.schema.json` and keeps
source-to-ComputeGraph, source-to-HAC-IR, source-to-runtime-plan, import, JIT,
and generated artifacts blocked.

The next dedicated surface gate is
[Package Import Sandbox Gate](PACKAGE_IMPORT_SANDBOX_GATE.md). The current
report at `examples/package_import_sandbox_gate.py` is validated by
`schemas/package_import_sandbox_gate_report.v0.schema.json` and keeps package
import, Python import, package code execution, entrypoint discovery, network,
filesystem, environment, subprocess, dynamic-library, plugin discovery, and
Source Intent from import blocked.

The third dedicated surface gate is
[Plugin Discovery Allowlist Gate](PLUGIN_DISCOVERY_ALLOWLIST_GATE.md). The
current report at `examples/plugin_discovery_allowlist_gate.py` is validated by
`schemas/plugin_discovery_allowlist_gate_report.v0.schema.json` and keeps
plugin discovery, entrypoint discovery, registry scans, filesystem scans,
frontend package import, Python import, plugin code execution, network,
subprocess, dynamic-library, device access, and capability claims from code
blocked.

The fourth dedicated surface gate is
[Triton JIT Execution Sandbox Gate](TRITON_JIT_EXECUTION_SANDBOX_GATE.md). The
current report at `examples/triton_jit_execution_sandbox_gate.py` is validated
by `schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json` and keeps
Triton JIT execution, kernel launch, generated artifact execution, device
access, kernel-cache access, backend binary emission, frontend package import,
Python import, plugin discovery, network, subprocess, and dynamic-library
surfaces blocked.

The fifth dedicated surface gate is
[Device Access Sandbox Gate](DEVICE_ACCESS_SANDBOX_GATE.md). The current report
at `examples/device_access_sandbox_gate.py` is validated by
`schemas/device_access_sandbox_gate_report.v0.schema.json` and keeps device
discovery, enumeration, driver calls, device handles, device memory allocation,
memory mapping, direct memory access, kernel launch, generated artifact
execution, subprocess, and dynamic-library surfaces blocked.

The sixth dedicated surface gate is
[Generated Artifact Quarantine Gate](GENERATED_ARTIFACT_QUARANTINE_GATE.md). The
current report at `examples/generated_artifact_quarantine_gate.py` is validated
by `schemas/generated_artifact_quarantine_gate_report.v0.schema.json` and keeps
artifact emission, writes, loads, executable permissions, artifact-cache access,
backend binary emission, generated artifact execution, device access, kernel
launch, subprocess, and dynamic-library surfaces blocked.
The seventh dedicated surface gate is
[Native Backend Execution Security Gate](NATIVE_BACKEND_EXECUTION_SECURITY_GATE.md).
The current report at `examples/native_backend_execution_security_gate.py` is
validated by `schemas/native_backend_execution_security_gate_report.v0.schema.json`
and keeps native backend execution, native plugin ABI loading, backend plugin
execution, symbol resolution, FFI calls, unsafe memory access, dynamic-library
loading, generated artifact execution, device access, kernel launch, and
subprocess surfaces blocked.
The compact full-perimeter artifact is
[Real Triton Surface Gate Completion](REAL_TRITON_SURFACE_GATE_COMPLETION.md).
The current report at `examples/real_triton_surface_gate_completion.py` is
validated by `schemas/real_triton_surface_gate_completion_report.v0.schema.json`
and binds admission plus all seven dedicated surface gates by digest while
keeping Real Triton admission blocked.

The [Source-To-Intent Next Syntax Slice](SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md)
now satisfies the parser RFC, next-syntax semantic corpus, Source Intent golden,
and semantic mapping fuzz/property prerequisites through
`examples/source_to_intent_next_syntax_slice.py` and
`schemas/source_to_intent_next_syntax_report.v0.schema.json`.

The [External Frontend Package Conformance](EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE.md)
report satisfies the external package conformance prerequisite through
`examples/external_frontend_package_conformance.py` and
`schemas/external_frontend_package_conformance_report.v0.schema.json`, while
keeping package import, plugin discovery, source ingestion, and JIT blocked.

Expand source-text to Source Intent IR only by adding parser budgets, semantic
mapping corpus cases, source-intent goldens, deterministic diagnostics, HAC-IR
review evidence, runtime-plan goldens, compiler decision-report goldens, and
security review evidence for the new syntax. External frontend proposals should
first publish a Source Intent Frontend Conformance report.
