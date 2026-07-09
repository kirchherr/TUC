# CI Replay For Admitted Slice

CI Replay For Admitted Slice v0 proves that the future
`bounded_source_buffer_to_source_intent_plain_data` slice is bound into CI as a
deterministic replay of the current admission evidence chain.

It does not admit direct source ingestion. It replays the existing evidence
reports, validates their contracts, binds their digests, and verifies that the
GitHub Actions workflow keeps read-only repository permissions, disables
checkout credential persistence, and runs the replay example explicitly.

Run it with:

```bash
python examples/ci_replay_for_admitted_slice.py
```

## What It Replays

The report binds these artifacts by digest:

- `bounded_source_buffer_api`
- `source_ingestion_sandbox_implementation`
- `parser_fuzz_negative_corpus_for_admitting_slice`
- `source_free_diagnostics_admission_tests`
- `source_to_intent_plain_data_output_golden_for_admitted_slice`

The replay is metadata-only and source-free. It does not store source text,
Source Intent payloads, tensor values, runtime handles, host paths, command
lines, device identifiers, generated code, backend artifacts, or executable
artifacts.

## First Slice Role

This artifact moves `ci_replay_for_admitted_slice` from missing admission
evidence into bound first-slice evidence. The Admitting Source Ingestion RFC and
Real Triton First Slice Plan remain blocked until
`maintainer_security_review_approval` exists.

## Contract

- Module: `src/tuc/frontend/admitted_slice_ci_replay.py`
- Example: `examples/ci_replay_for_admitted_slice.py`
- Schema: `schemas/ci_replay_for_admitted_slice_report.v0.schema.json`
- Golden: `tests/golden/frontend/ci_replay_for_admitted_slice_report.json`
- Tests: `tests/test_ci_replay_for_admitted_slice.py`
- RFC: `rfcs/0264-ci-replay-for-admitted-slice.md`
- Workflow: `.github/workflows/ci.yml`
- First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
- Admitting Source Ingestion RFC: [Admitting Source Ingestion RFC](ADMITTING_SOURCE_INGESTION_RFC.md)
- Source-To-Intent Plain-Data Output Golden: [Source-To-Intent Plain-Data Output Golden For Admitted Slice](SOURCE_TO_INTENT_PLAIN_DATA_OUTPUT_GOLDEN_FOR_ADMITTED_SLICE.md)
