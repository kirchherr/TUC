# Source-Free Diagnostics Admission Tests

Source-Free Diagnostics Admission Tests v0 prove that diagnostics for the
future admitting `bounded_source_buffer_to_source_intent_plain_data` slice stay
bounded, reason-code based, and source-free.

They do not implement a parser, do not admit source ingestion, and do not emit
Source Intent plain data. The current report keeps:

```text
diagnostics_status = complete_non_admitting
source_to_intent_plain_data = false
source_to_compute_graph = false
source_to_hac_ir = false
source_to_runtime_plan = false
```

Run it with:

```bash
python examples/source_free_diagnostics_admission_tests.py
```

## What It Binds

The report binds Parser Fuzz Negative Corpus For Admitting Slice evidence by
SHA-256 metadata digest. Each negative corpus case produces one public
diagnostic record containing only:

- case ID;
- source digest;
- diagnostic class;
- diagnostic code;
- reason code;
- message template ID;
- bounded diagnostic byte count;
- explicit false flags for Source Intent, graph, HAC-IR, and runtime-plan
  outputs.

## Security Boundary

The report is digest-only and source-free. It does not serialize source text,
source excerpts, source locations, Source Intent payloads, tensor values,
runtime handles, host paths, command lines, device identifiers, plugin
entrypoints, generated code, backend artifacts, native benchmark output, or
executable artifacts.

It does not import external packages, discover plugins, run Triton JIT, access
devices, load dynamic libraries, spawn subprocesses, touch the network, emit
generated artifacts, produce HAC-IR, produce runtime plans, or authorize
compiler shortcuts from source.

## Contract

- Module: `src/tuc/frontend/source_free_diagnostics_admission.py`
- Example: `examples/source_free_diagnostics_admission_tests.py`
- Schema: `schemas/source_free_diagnostics_admission_tests_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_free_diagnostics_admission_tests_report.json`
- Tests: `tests/test_source_free_diagnostics_admission_tests.py`
- RFC: `rfcs/0262-source-free-diagnostics-admission-tests.md`
- Parser Fuzz Negative Corpus: [Parser Fuzz Negative Corpus For Admitting Slice](PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md)
- First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
- Admitting Source Ingestion RFC: [Admitting Source Ingestion RFC](ADMITTING_SOURCE_INGESTION_RFC.md)
