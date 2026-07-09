# Parser Fuzz Negative Corpus For Admitting Slice

Parser Fuzz Negative Corpus v0 is a source-free evidence artifact for the future
admitting `bounded_source_buffer_to_source_intent_plain_data` slice.

It is complete as a corpus, but it remains non-admitting:

```text
corpus_status = complete_non_admitting
source_to_intent_plain_data = false
source_to_compute_graph = false
source_to_hac_ir = false
source_to_runtime_plan = false
```

Run it with:

```bash
python examples/parser_fuzz_negative_corpus_for_admitting_slice.py
```

## Scope

The corpus defines deterministic private negative/fuzz seeds that a future
admitting parser must reject before lowering. Public evidence contains only:

- source digests;
- byte and line counts;
- expected rejection categories and reason codes;
- mutation-family coverage;
- source-ingestion sandbox result metadata;
- a digest binding to Source Ingestion Sandbox Implementation evidence.

It does not serialize raw source text, Source Intent plain data, Source Intent
payloads, ComputeGraph, TLIR, HAC-IR, HS-IR, runtime plans, Python function
objects, generated artifacts, backend artifacts, host paths, commands, device
identifiers, or runtime handles.

## Coverage

The corpus covers these rejection categories:

- hardware-specific source hints;
- invalid shape profiles;
- malformed syntax;
- source/resource budget overflow;
- unsafe execution surfaces;
- unsupported parser semantics.

The corpus also covers mutation families for AST boundaries, budget boundaries,
hardware hints, shape profiles, syntax boundaries, and trust boundaries.

## First Slice Role

This closes the `parser_fuzz_negative_corpus_for_admitting_slice` prerequisite
in the Real Triton First Slice Plan. The next bound evidence is
`source_free_diagnostics_admission_tests`, which proves the public rejection
diagnostics for this corpus stay source-free. The remaining blockers are:

- Source Intent plain-data output goldens;
- CI replay for the admitted slice;
- maintainer security review approval.
## Security Boundary

The corpus is not a parser and does not call a parser. It uses the source
ingestion sandbox only to bind each private seed to source-free metadata. It
does not import packages, evaluate decorators, run Triton JIT, access devices,
discover plugins, spawn subprocesses, touch the network, load dynamic libraries,
execute native backends, produce compiler artifacts, or authorize source-to-HAC-
IR or source-to-runtime-plan shortcuts.

## Contract

- API module: `src/tuc/frontend/parser_fuzz_negative_corpus.py`
- Example: `examples/parser_fuzz_negative_corpus_for_admitting_slice.py`
- Schema: `schemas/parser_fuzz_negative_corpus_for_admitting_slice_report.v0.schema.json`
- Golden: `tests/golden/frontend/parser_fuzz_negative_corpus_for_admitting_slice_report.json`
- Tests: `tests/test_parser_fuzz_negative_corpus_for_admitting_slice.py`
- RFC: `rfcs/0261-parser-fuzz-negative-corpus-for-admitting-slice.md`
- Source-Free Diagnostics Admission Tests Module: `src/tuc/frontend/source_free_diagnostics_admission.py`
- Source-Free Diagnostics Admission Tests Example: `examples/source_free_diagnostics_admission_tests.py`
- Source-Free Diagnostics Admission Tests Schema: `schemas/source_free_diagnostics_admission_tests_report.v0.schema.json`
- Source-Free Diagnostics Admission Tests Golden: `tests/golden/frontend/source_free_diagnostics_admission_tests_report.json`
- Source-Free Diagnostics Admission Tests Doc: `docs/SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md`
- Source-Free Diagnostics Admission Tests RFC: `rfcs/0262-source-free-diagnostics-admission-tests.md`
- First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
- Admitting Source Ingestion RFC: [Admitting Source Ingestion RFC](ADMITTING_SOURCE_INGESTION_RFC.md)
- Source Ingestion Sandbox Implementation: [Source Ingestion Sandbox Implementation](SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md)