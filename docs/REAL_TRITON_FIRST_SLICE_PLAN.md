# Real Triton First Slice Plan

Real Triton First Slice Plan v0 is the data-only plan for the first possible
admitting Real Triton integration slice.

It does not admit Real Triton integration. The current report keeps:

```text
admitted = false
source_ingestion_admission_ready = false
admission_status = blocked
```

Run it with:

```bash
python examples/real_triton_first_slice_plan.py
```

## What It Binds

The plan binds ten current artifacts by SHA-256 metadata digest:

- Real Triton Integration Admission Gate.
- Real Triton Surface Gate Completion.
- Source Ingestion Quarantine Gate.
- Admitting Source Ingestion RFC.
- Bounded Source Buffer API.
- Source Ingestion Sandbox Implementation.
- Parser Fuzz Negative Corpus For Admitting Slice.
- Source-Free Diagnostics Admission Tests.
- Source-To-Intent Research Source Runtime Smoke.
- Source-To-Intent Research Kernel Ingress Proof Bundle.

## Meaning

The plan identifies `direct_source_ingestion` as the first candidate surface
for a future admitting slice. It now binds the requirements-only Admitting
Source Ingestion RFC, the Bounded Source Buffer API, the Source Ingestion
Sandbox Implementation, Parser Fuzz Negative Corpus, and Source-Free
Diagnostics Admission Tests, but still records the golden, replay, and
maintainer-review evidence required before that surface can become admitting.

The remaining Real Triton surfaces stay blocked:

- frontend package import;
- plugin discovery;
- Triton JIT execution;
- device access;
- generated artifact execution;
- native backend execution.

## Missing Admission Evidence

Before `direct_source_ingestion` can become admitting, TUC still requires:

- source-to-Intent plain-data output goldens;
- CI replay for the admitted slice;
- maintainer security review approval.

## Security Boundary

The report is digest-only and source-free. It does not serialize source text,
Source Intent payloads, tensor values, runtime handles, host paths, command
lines, device identifiers, plugin entrypoints, generated code, backend
artifacts, native benchmark output, or executable artifacts.

It does not import external packages, discover plugins, run Triton JIT, access
devices, load dynamic libraries, spawn subprocesses, touch the network, emit
generated artifacts, or authorize source-to-HAC-IR or source-to-runtime-plan
shortcuts.

## Contract

- Example: `examples/real_triton_first_slice_plan.py`
- Schema: `schemas/real_triton_first_slice_plan_report.v0.schema.json`
- Golden: `tests/golden/frontend/real_triton_first_slice_plan_report.json`
- Tests: `tests/test_real_triton_first_slice_plan.py`
- RFC: `rfcs/0257-real-triton-first-slice-plan.md`
- Admitting Source Ingestion RFC Example: `examples/admitting_source_ingestion_rfc.py`
- Admitting Source Ingestion RFC Schema: `schemas/admitting_source_ingestion_rfc_report.v0.schema.json`
- Admitting Source Ingestion RFC Golden: `tests/golden/frontend/admitting_source_ingestion_rfc_report.json`
- Admitting Source Ingestion RFC Doc: `docs/ADMITTING_SOURCE_INGESTION_RFC.md`
- Admitting Source Ingestion RFC: `rfcs/0258-admitting-source-ingestion-rfc.md`
- Bounded Source Buffer API Module: `src/tuc/frontend/bounded_source_buffer.py`
- Bounded Source Buffer API Example: `examples/bounded_source_buffer_api.py`
- Bounded Source Buffer API Schema: `schemas/bounded_source_buffer_api_report.v0.schema.json`
- Bounded Source Buffer API Golden: `tests/golden/frontend/bounded_source_buffer_api_report.json`
- Bounded Source Buffer API Doc: `docs/BOUNDED_SOURCE_BUFFER_API.md`
- Bounded Source Buffer API RFC: `rfcs/0259-bounded-source-buffer-api.md`
- Source Ingestion Sandbox Module: `src/tuc/frontend/source_ingestion_sandbox.py`
- Source Ingestion Sandbox Example: `examples/source_ingestion_sandbox_implementation.py`
- Source Ingestion Sandbox Schema: `schemas/source_ingestion_sandbox_implementation_report.v0.schema.json`
- Source Ingestion Sandbox Golden: `tests/golden/frontend/source_ingestion_sandbox_implementation_report.json`
- Source Ingestion Sandbox Doc: `docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md`
- Source Ingestion Sandbox RFC: `rfcs/0260-source-ingestion-sandbox-implementation.md`
- Parser Fuzz Negative Corpus Module: `src/tuc/frontend/parser_fuzz_negative_corpus.py`
- Parser Fuzz Negative Corpus Example: `examples/parser_fuzz_negative_corpus_for_admitting_slice.py`
- Parser Fuzz Negative Corpus Schema: `schemas/parser_fuzz_negative_corpus_for_admitting_slice_report.v0.schema.json`
- Parser Fuzz Negative Corpus Golden: `tests/golden/frontend/parser_fuzz_negative_corpus_for_admitting_slice_report.json`
- Parser Fuzz Negative Corpus Doc: `docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md`
- Parser Fuzz Negative Corpus RFC: `rfcs/0261-parser-fuzz-negative-corpus-for-admitting-slice.md`
- Source-Free Diagnostics Admission Tests Module: `src/tuc/frontend/source_free_diagnostics_admission.py`
- Source-Free Diagnostics Admission Tests Example: `examples/source_free_diagnostics_admission_tests.py`
- Source-Free Diagnostics Admission Tests Schema: `schemas/source_free_diagnostics_admission_tests_report.v0.schema.json`
- Source-Free Diagnostics Admission Tests Golden: `tests/golden/frontend/source_free_diagnostics_admission_tests_report.json`
- Source-Free Diagnostics Admission Tests Doc: `docs/SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md`
- Source-Free Diagnostics Admission Tests RFC: `rfcs/0262-source-free-diagnostics-admission-tests.md`
- Admission Gate: [Real Triton Integration Admission Gate](REAL_TRITON_INTEGRATION_ADMISSION_GATE.md)
- Surface Gate Completion: [Real Triton Surface Gate Completion](REAL_TRITON_SURFACE_GATE_COMPLETION.md)
