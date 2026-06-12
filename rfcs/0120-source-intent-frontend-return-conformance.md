# RFC 0120: Source Intent Frontend Return Conformance

- Status: Accepted
- Related:
  - [Source Intent Frontend Conformance](../docs/SOURCE_INTENT_FRONTEND_CONFORMANCE.md)
  - [Source Intent Return Semantics](../docs/SOURCE_INTENT_RETURN_SEMANTICS.md)
  - [Source Intent Runtime Returns](../docs/SOURCE_INTENT_RUNTIME_RETURNS.md)
  - `tests/golden/frontend/source_intent_frontend_conformance_report.json`

## Summary

Extend Source Intent Frontend Conformance fixtures so external frontend authors
can prove explicit public return intent before any source parser, frontend
package loading, backend plugin discovery, or generated artifact execution is
accepted.

## Motivation

Source Intent Return Semantics and Source Intent Runtime Returns define the
frontend-to-runtime return chain, but external frontend conformance previously
covered only generic Source Intent intake and neutral planning. A frontend could
pass conformance without demonstrating that it emits valid public return intent
or fails closed on malformed returns.

## Design

The existing Source Intent Frontend Conformance report shape remains unchanged.
The conformance suite now includes:

- one accepted Source Intent payload with explicit public returns
- rejected return to an unknown tensor
- rejected return to an intermediate, non-terminal tensor
- rejected duplicate public return names

Accepted cases that contain `returns` must also preserve return metadata across
Source Intent Metadata Conversion:

- `frontend.source_intent_return_policy`
- `frontend.source_intent_return_aliases`

The report remains deterministic and metadata-only.

## Non-Goals

- adding source parsing
- changing the Source Intent Frontend Conformance report schema
- requiring public returns for every Source Intent frontend case
- executing frontend packages or generated artifacts
- certifying backend plugins

## Security

All checks operate on caller-provided in-memory plain data. Diagnostics continue
to report case names, stages, and exception types only; raw payloads, source
text, paths, plugin entrypoints, backend artifacts, and generated code remain
excluded from the report.

Malformed returns fail closed at Source Intent Intake. Valid returns must
survive metadata conversion as bounded labels rather than executable hooks.

## Acceptance Criteria

- Example conformance report includes an accepted explicit-return case.
- Example conformance report includes rejected malformed-return cases.
- Accepted explicit-return cases preserve return policy and alias metadata.
- Source Intent Frontend Conformance golden is updated.
- Full test suite remains green.
