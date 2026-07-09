# Source-To-Intent Plain-Data Output Golden For Admitted Slice

Source-To-Intent Plain-Data Output Golden For Admitted Slice v0 proves that the
future `bounded_source_buffer_to_source_intent_plain_data` admitting slice has a
reviewable Source Intent plain-data output shape before source ingestion becomes
admitting.

It does not admit direct source ingestion and does not implement the future
parser. It consumes explicit research parser results as data, revalidates their
`source_intent.v0` payloads through Source Intent Intake, and emits a digest-only
report plus a separate reviewable Source Intent plain-data golden.

Run it with:

```bash
python examples/source_to_intent_plain_data_output_golden_for_admitted_slice.py
python examples/source_to_intent_plain_data_output_golden_for_admitted_slice.py --source-intent
```

## What It Proves

The report proves that the current admitted-slice candidate has:

- two reviewable Source Intent plain-data golden cases;
- coverage for `elementwise`, `matmul`, `reduction`, and `softmax`;
- Source Intent Intake validation for each plain-data payload;
- stable digests for the plain-data payloads;
- a digest binding to Source-Free Diagnostics Admission Tests;
- no direct source ingestion admission.

## Security Boundary

The report is source-free and digest-only. It does not serialize source text,
Source Intent payloads, tensor values, runtime handles, host paths, command
lines, device identifiers, plugin entrypoints, generated code, backend artifacts,
native benchmark output, or executable artifacts.

The separate `--source-intent` output is a reviewable plain-data golden, not a
compiler artifact. It is not connected to metadata lowering, `ComputeGraph`,
HAC-IR, HS-IR, runtime planning, Triton JIT, device access, package import,
plugin discovery, generated artifact execution, subprocesses, network, or
dynamic libraries.

## First Slice Role

This artifact moves `source_to_intent_plain_data_output_golden_for_admitted_slice`
from missing admission evidence into bound first-slice evidence. The Admitting
Source Ingestion RFC and Real Triton First Slice Plan remain blocked until CI
replay for the admitted slice and maintainer security review approval exist.

## Contract

- Module: `src/tuc/frontend/source_to_intent_admitted_slice_golden.py`
- Example: `examples/source_to_intent_plain_data_output_golden_for_admitted_slice.py`
- Schema: `schemas/source_to_intent_plain_data_output_golden_for_admitted_slice_report.v0.schema.json`
- Report Golden: `tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_report.json`
- Source Intent Golden: `tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_source_intent.json`
- Tests: `tests/test_source_to_intent_plain_data_output_golden_for_admitted_slice.py`
- RFC: `rfcs/0263-source-to-intent-plain-data-output-golden-for-admitted-slice.md`
- First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
- Admitting Source Ingestion RFC: [Admitting Source Ingestion RFC](ADMITTING_SOURCE_INGESTION_RFC.md)
- Source-Free Diagnostics Admission Tests: [Source-Free Diagnostics Admission Tests](SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md)
