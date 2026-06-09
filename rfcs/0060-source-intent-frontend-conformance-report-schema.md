# RFC 0060: Source Intent Frontend Conformance Report Schema

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC publishes a machine-readable JSON Schema for Source Intent Frontend
Conformance reports:

```text
schemas/source_intent_frontend_conformance_report.v0.schema.json
```

This RFC does not add source parsing, file loading, frontend module imports,
preflight-to-intent conversion, plugin discovery, backend lowering,
generated-artifact execution, device access, or production report ingestion.

## Motivation

RFC 0059 introduced deterministic frontend conformance reports. External
frontend authors now need a stable schema for review artifacts so maintainers
can compare conformance evidence without importing or executing third-party
frontend code.

## Decision

Add `schemas/source_intent_frontend_conformance_report.v0.schema.json` using
JSON Schema draft 2020-12.

The schema documents:

- the report schema version
- frontend name
- checked case names
- accepted and rejected case counts
- pass/fail state
- bounded issue objects

All object shapes use `additionalProperties: false`.

## Security Boundary

The report schema is not a production validator for frontend payloads. The
trusted conformance path remains
`run_source_intent_frontend_conformance(frontend_name, cases)`, followed by
`dump_source_intent_frontend_conformance_report(report)`.

The schema must not include raw frontend payloads, source text, paths, plugin
entrypoints, backend artifacts, generated code, environment data, or device
references.

It must not add source parsing or report-to-compiler ingestion.

## Evidence

The implementation adds tests that verify:

- schema version matches
  `SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION`
- case and issue limits match the runtime conformance limit
- all object shapes fail closed with `additionalProperties: false`
- raw payload, source-text, path, plugin, and backend-artifact fields are absent
- the golden conformance report matches the schema's required shape
- docs reference
  `schemas/source_intent_frontend_conformance_report.v0.schema.json`

## Consequences

- Frontend conformance reports become easier to review across implementations.
- Maintainers get a stable report contract without trusting third-party
  frontend code.
- Source Intent remains a data-only, hardware-independent frontend boundary.

## Rejected Alternatives

1. Store raw accepted and rejected payloads inside conformance reports.

   Rejected because reports should not amplify attacker-controlled payloads or
   source text.

2. Make report schemas validate frontend payload semantics.

   Rejected because payload semantics belong to Source Intent Intake and
   conformance execution, not the report artifact.

3. Add a production report ingestion API.

   Rejected because accepting third-party report files as inputs is outside
   this slice and would require its own threat model.
