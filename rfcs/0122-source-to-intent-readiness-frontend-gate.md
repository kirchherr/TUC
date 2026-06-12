# RFC 0122: Source-To-Intent Readiness Frontend Gate Evidence

- Status: Accepted
- Related:
  - [Source-To-Intent Readiness Report](../docs/SOURCE_TO_INTENT_READINESS.md)
  - [Source-To-Intent Parser Gate](../docs/SOURCE_TO_INTENT_PARSER_GATE.md)
  - [Source Intent Frontend Conformance Gate](../docs/SOURCE_INTENT_FRONTEND_CONFORMANCE_GATE.md)
  - [RFC 0121](0121-source-intent-frontend-conformance-gate.md)

## Summary

Add `source_intent_frontend_conformance_gate` to the required Source-To-Intent
Readiness evidence IDs.

## Motivation

Future source-to-intent parser proposals must prove that emitted
`source_intent.v0` plain data passes Source Intent Frontend Conformance. After
RFC 0121 introduced a CI-facing Frontend Conformance Gate, readiness should
require that gate output rather than only the raw conformance report.

This keeps parser proposals aligned with merge-time evidence and required
public-return conformance coverage.

## Design

`SOURCE_TO_INTENT_REQUIRED_EVIDENCE` now requires:

```text
source_intent_frontend_conformance_gate
```

The existing readiness report schema version remains stable because the report
already models evidence IDs as bounded strings from the canonical required
evidence list. The golden blocked report is updated to show the new missing
evidence item.

## Non-Goals

- implementing source parsing
- changing readiness report shape or schema version
- accepting preflight-to-intent conversion
- changing Source Intent Frontend Conformance Gate semantics
- loading frontend packages or executing generated artifacts

## Security

The readiness report remains metadata-only. It accepts explicit evidence IDs
and booleans, rejects unknown and duplicate IDs, and does not include raw source
text, raw frontend payloads, paths, plugin entrypoints, generated code, device
handles, backend artifacts, environment variables, or cache locations.

## Acceptance Criteria

- `SOURCE_TO_INTENT_REQUIRED_EVIDENCE` includes
  `source_intent_frontend_conformance_gate`.
- A parser proposal with all old evidence but no frontend conformance gate
  remains blocked.
- Source-To-Intent Readiness golden includes the new missing evidence item.
- Source-To-Intent Parser Gate docs mention the gate output.
- Full test suite remains green.
