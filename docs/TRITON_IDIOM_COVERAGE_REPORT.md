# Triton Idiom Coverage Report

Triton Idiom Coverage Report is a diagnostic artifact for the safe Triton-like
metadata path. It records which Triton-like compute idioms are covered by
schema-versioned metadata examples and deterministic golden evidence.

It is not a Triton source parser, not a `@triton.jit` bridge, not a Python
object inspector, and not a compiler lowering path.

## Contract

- Report schema: `schemas/triton_idiom_coverage_report.v0.schema.json`
- Report schema version: `tuc.triton_idiom_coverage_report.v0`
- Coverage contract: `triton_idiom_coverage.execution_free.v0`
- Evidence type: `TritonIdiomCoverage`
- API: `build_triton_idiom_coverage_report(proposal_name, coverages)`
- Dump API: `dump_triton_idiom_coverage_report(report)`
- Example: `examples/triton_idiom_coverage_report.py`
- Golden: `tests/golden/frontend/triton_idiom_coverage_report.json`
- Tests: `tests/test_triton_idiom_coverage_report.py`
- Schema tests: `tests/test_triton_idiom_coverage_schema.py`

## What It Records

Each coverage entry records only bounded identifiers:

- idiom identifier
- MVP operation family
- metadata example identifier
- intake golden identifier
- HAC-IR golden identifier
- runtime-plan golden identifier
- compiler-decision golden identifier
- coverage status

The report can show that a Triton-like idiom is covered through metadata and
goldens. It cannot show that Triton source syntax is parsed correctly.

## Security Boundary

The report must not include source text, Python source, host paths, command
lines, environment variables, device identifiers, plugin entrypoints, generated
code, backend artifacts, raw benchmark output, or raw compiler artifacts.

`direct_triton_source_ingestion` is always `false`.

`parser_status` is always `direct_triton_source_ingestion_blocked`.

The report exists so future Triton idiom work can expand credibility without
weakening the source parser gate.

## Ready Semantics

`triton_idiom_coverage_ready` means:

- at least one coverage entry is present
- every entry is `metadata_golden_covered`
- every entry references metadata, intake, HAC-IR, runtime-plan, and
  compiler-decision evidence identifiers

It does not authorize direct Triton source ingestion.

It does not imply native performance.

It does not approve generated artifact execution.
