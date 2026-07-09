# Admitting Source Ingestion RFC

Admitting Source Ingestion RFC v0 is a requirements-only review artifact for
the first possible `direct_source_ingestion` admitting slice.

It does not implement source ingestion and does not admit source ingestion. The
current report keeps:

```text
admitted = false
implementation_status = not_implemented
source_ingestion_admission_ready = false
```

Run it with:

```bash
python examples/admitting_source_ingestion_rfc.py
```

## Scope

The candidate target slice is:

```text
bounded_source_buffer_to_source_intent_plain_data
```

Allowed outputs remain limited to Source Intent plain data, sanitized
diagnostics, and metadata digests. The RFC denies direct output of
`ComputeGraph`, HAC-IR, HS-IR, runtime plans, generated artifacts, Python
function objects, and backend artifacts.

## Remaining Evidence

The `bounded_source_buffer_api`, `source_ingestion_sandbox_implementation`, `parser_fuzz_negative_corpus_for_admitting_slice`, `source_free_diagnostics_admission_tests`, and `source_to_intent_plain_data_output_golden_for_admitted_slice` prerequisites are now covered. Before source ingestion can become admitting, TUC still requires:

- CI replay for the admitted slice;
- maintainer security review approval.

## Security Boundary

The report is digest-only and source-free. It does not serialize source text,
Source Intent payloads, tensor values, runtime handles, host paths, command
lines, device identifiers, plugin entrypoints, generated code, backend
artifacts, native benchmark output, or executable artifacts.

It does not import external packages, discover plugins, run Triton JIT, access
devices, load dynamic libraries, spawn subprocesses, touch the network, emit
generated artifacts, produce HAC-IR, produce runtime plans, or authorize
compiler shortcuts from source.

## Contract

- Example: `examples/admitting_source_ingestion_rfc.py`
- Schema: `schemas/admitting_source_ingestion_rfc_report.v0.schema.json`
- Golden: `tests/golden/frontend/admitting_source_ingestion_rfc_report.json`
- Tests: `tests/test_admitting_source_ingestion_rfc.py`
- RFC: `rfcs/0258-admitting-source-ingestion-rfc.md`
- First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
- Bounded Source Buffer API: [Bounded Source Buffer API](BOUNDED_SOURCE_BUFFER_API.md)
- Bounded Source Buffer API Doc: `docs/BOUNDED_SOURCE_BUFFER_API.md`
- Bounded Source Buffer API Module: `src/tuc/frontend/bounded_source_buffer.py`
- Bounded Source Buffer API Example: `examples/bounded_source_buffer_api.py`
- Bounded Source Buffer API Schema: `schemas/bounded_source_buffer_api_report.v0.schema.json`
- Bounded Source Buffer API Golden: `tests/golden/frontend/bounded_source_buffer_api_report.json`
- Bounded Source Buffer API RFC: `rfcs/0259-bounded-source-buffer-api.md`
- Source Ingestion Sandbox Implementation: [Source Ingestion Sandbox Implementation](SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md)
- Source Ingestion Sandbox Doc: `docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md`
- Source Ingestion Sandbox Module: `src/tuc/frontend/source_ingestion_sandbox.py`
- Source Ingestion Sandbox Example: `examples/source_ingestion_sandbox_implementation.py`
- Source Ingestion Sandbox Schema: `schemas/source_ingestion_sandbox_implementation_report.v0.schema.json`
- Source Ingestion Sandbox Golden: `tests/golden/frontend/source_ingestion_sandbox_implementation_report.json`
- Source Ingestion Sandbox RFC: `rfcs/0260-source-ingestion-sandbox-implementation.md`
- Parser Fuzz Negative Corpus: [Parser Fuzz Negative Corpus For Admitting Slice](PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md)
- Parser Fuzz Negative Corpus Doc: `docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md`
- Parser Fuzz Negative Corpus Module: `src/tuc/frontend/parser_fuzz_negative_corpus.py`
- Parser Fuzz Negative Corpus Example: `examples/parser_fuzz_negative_corpus_for_admitting_slice.py`
- Parser Fuzz Negative Corpus Schema: `schemas/parser_fuzz_negative_corpus_for_admitting_slice_report.v0.schema.json`
- Parser Fuzz Negative Corpus Golden: `tests/golden/frontend/parser_fuzz_negative_corpus_for_admitting_slice_report.json`
- Parser Fuzz Negative Corpus RFC: `rfcs/0261-parser-fuzz-negative-corpus-for-admitting-slice.md`
- Source-Free Diagnostics Admission Tests: [Source-Free Diagnostics Admission Tests](SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md)
- Source-Free Diagnostics Admission Tests Doc: `docs/SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md`
- Source-Free Diagnostics Admission Tests Module: `src/tuc/frontend/source_free_diagnostics_admission.py`
- Source-Free Diagnostics Admission Tests Example: `examples/source_free_diagnostics_admission_tests.py`
- Source-Free Diagnostics Admission Tests Schema: `schemas/source_free_diagnostics_admission_tests_report.v0.schema.json`
- Source-Free Diagnostics Admission Tests Golden: `tests/golden/frontend/source_free_diagnostics_admission_tests_report.json`
- Source-Free Diagnostics Admission Tests RFC: `rfcs/0262-source-free-diagnostics-admission-tests.md`
- Source-To-Intent Plain-Data Output Golden: [Source-To-Intent Plain-Data Output Golden For Admitted Slice](SOURCE_TO_INTENT_PLAIN_DATA_OUTPUT_GOLDEN_FOR_ADMITTED_SLICE.md)
- Source-To-Intent Plain-Data Output Golden Doc: `docs/SOURCE_TO_INTENT_PLAIN_DATA_OUTPUT_GOLDEN_FOR_ADMITTED_SLICE.md`
- Source-To-Intent Plain-Data Output Golden Module: `src/tuc/frontend/source_to_intent_admitted_slice_golden.py`
- Source-To-Intent Plain-Data Output Golden Example: `examples/source_to_intent_plain_data_output_golden_for_admitted_slice.py`
- Source-To-Intent Plain-Data Output Golden Schema: `schemas/source_to_intent_plain_data_output_golden_for_admitted_slice_report.v0.schema.json`
- Source-To-Intent Plain-Data Output Golden Report Golden: `tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_report.json`
- Source-To-Intent Plain-Data Output Golden Source Intent Golden: `tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_source_intent.json`
- Source-To-Intent Plain-Data Output Golden RFC: `rfcs/0263-source-to-intent-plain-data-output-golden-for-admitted-slice.md`
