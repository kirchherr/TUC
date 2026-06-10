# Source Intent Frontend Conformance Report Schema

TUC publishes a machine-readable JSON Schema for Source Intent Frontend
Conformance reports:

```text
schemas/source_intent_frontend_conformance_report.v0.schema.json
```

The schema documents the deterministic review artifact emitted by
`dump_source_intent_frontend_conformance_report(report)`.

## Contract

- Report schema version:
  `tuc.source_intent_frontend_conformance_report.v0`
- JSON Schema draft: 2020-12
- Runtime report API:
  `dump_source_intent_frontend_conformance_report(report)`
- Schema file:
  `schemas/source_intent_frontend_conformance_report.v0.schema.json`
- Golden report:
  `tests/golden/frontend/source_intent_frontend_conformance_report.json`

The schema defines:

- frontend name
- checked case names
- accepted and rejected case counts
- pass/fail flag
- bounded conformance issues
- report schema version

All object shapes use `additionalProperties: false`.

## Security Boundary

The schema is an interoperability artifact for generated conformance reports.
It is not a production validator for frontend payloads.

It does not add:

- source parsing
- file loading
- frontend package imports
- preflight report ingestion
- plugin discovery
- backend lowering
- generated artifact execution
- device access

The report schema intentionally excludes raw frontend payloads, source text,
paths, plugin entrypoints, backend artifacts, and generated code.

The trusted conformance path remains
`run_source_intent_frontend_conformance(frontend_name, cases)`, followed by
`dump_source_intent_frontend_conformance_report(report)`.

## Versioning

Changes to the report schema must update:

- `schemas/source_intent_frontend_conformance_report.v0.schema.json`
- `SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION`
- Source Intent Frontend Conformance tests
- Source Intent Frontend Conformance docs
- RFC evidence

Incompatible schema changes require a new schema version instead of silently
changing the v0 report contract.
