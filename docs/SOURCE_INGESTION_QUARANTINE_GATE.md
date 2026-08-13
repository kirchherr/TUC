# Source Ingestion Quarantine Gate

Source Ingestion Quarantine Gate v0 is the first dedicated surface gate behind
Real Triton Integration Admission.

It establishes a source-buffer quarantine boundary without admitting direct
source ingestion into compiler artifacts. The current report is data-only and
does not parse arbitrary source into `ComputeGraph`, TLIR, HAC-IR, HS-IR,
runtime plans, backend decisions, generated artifacts, or executable code.

## Contract

- Report schema:
  `schemas/source_ingestion_quarantine_gate_report.v0.schema.json`
- Report schema version:
  `tuc.source_ingestion_quarantine_gate_report.v0`
- Gate contract:
  `source_ingestion_quarantine_gate.data_only.v0`
- Example: `examples/source_ingestion_quarantine_gate.py`
- Golden:
  `tests/golden/frontend/source_ingestion_quarantine_gate_report.json`
- Tests: `tests/test_source_ingestion_quarantine_gate.py`
- RFC: `rfcs/0245-source-ingestion-quarantine-gate.md`

## Meaning

The gate binds digest-only evidence for:

- Real Triton Integration Admission Gate;
- Source-To-Intent Parser Gate;
- Triton Source Preflight;
- Triton Source Threat Model.

The current status is:

- `gate_status = quarantine_only`;
- `quarantine_boundary_established = true`;
- `admission_effect = does_not_admit_direct_source_ingestion`;
- `direct_source_ingestion = false`.

This means TUC has a reviewable quarantine policy for source buffers, not a
general source frontend.

## Required Controls

The gate requires:

- bounded source buffers;
- decode-only handling before preflight;
- execution-free AST preflight;
- fail-closed violations;
- untrusted-input treatment;
- no source-to-ComputeGraph path;
- no source-to-HAC-IR path;
- no Python import;
- no Triton JIT;
- no device access;
- no generated artifacts;
- no raw source serialization;
- sanitized diagnostics only;
- digest-only public evidence.

## Security Boundary

The report must not contain raw source, Python source, host paths, command
lines, environment variables, device identifiers, runtime handles, plugin
entrypoints, generated code, backend artifacts, raw benchmark output, raw
timing samples, or executable permissions.

Future parser work may only pass through this boundary if it adds its own
corpus, diagnostics, budgets, conformance evidence, negative tests, and review
gate without weakening these quarantine controls.
