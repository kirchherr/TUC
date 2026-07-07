# Triton Integration Readiness Report

Triton Integration Readiness v0 is a data-only checkpoint for the next roadmap
milestone: real Triton-facing integration after the current abstraction proof
is stable.

It does not enable direct Triton source ingestion, execute `@triton.jit`, import
Python modules, inspect Python function objects, access devices, discover
plugins, or create generated artifacts.

## Contract

- Report schema: `schemas/triton_integration_readiness_report.v0.schema.json`
- Report schema version: `tuc.triton_integration_readiness_report.v0`
- Readiness contract: `triton_integration_readiness.data_only.v0`
- Example: `examples/triton_integration_readiness.py`
- Golden: `tests/golden/frontend/triton_integration_readiness_report.json`
- Tests: `tests/test_triton_integration_readiness.py`
- RFC: `rfcs/0241-triton-integration-readiness.md`

## Current Meaning

The current report is intentionally **not ready**.

It records that TUC already has credible prerequisites:

- Triton source threat model;
- execution-free source preflight;
- Triton idiom coverage through schema-versioned metadata;
- Source Intent plain-data contracts;
- Source Intent Frontend Conformance Gate;
- Source-To-Intent Parser Gate;
- explicit Source-To-Intent Research Parser;
- Kernel Ingress research evidence;
- Proof Of Backend Equivalence;
- Layout Conversion Evidence;
- [Source-To-Intent Next Syntax Slice](SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md),
  including `examples/source_to_intent_next_syntax_slice.py` and
  `schemas/source_to_intent_next_syntax_report.v0.schema.json`.
  Canonical doc path: `docs/SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md`.

It also records one missing prerequisite before broader Triton-facing
integration can move beyond the current research slice:

- external frontend package conformance.

Direct Triton source ingestion and Triton JIT execution remain blocked by
policy in this report.

## Security Boundary

The report is metadata-only. It must not contain source text, Python source,
function objects, host paths, command lines, environment variables, device
identifiers, runtime handles, backend artifacts, generated code, plugin
entrypoints, raw benchmark output, raw timing samples, or executable
permissions.

Future work must make `readiness_ready = true` before any broader Triton-facing
integration can count as roadmap progress. Even then, readiness is a review
condition, not permission to execute user source or native backend code.