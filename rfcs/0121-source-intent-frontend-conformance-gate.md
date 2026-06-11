# RFC 0121: Source Intent Frontend Conformance Gate

- Status: Accepted
- Related:
  - [Source Intent Frontend Conformance](../docs/SOURCE_INTENT_FRONTEND_CONFORMANCE.md)
  - [Source Intent Frontend Conformance Gate](../docs/SOURCE_INTENT_FRONTEND_CONFORMANCE_GATE.md)
  - [RFC 0120](0120-source-intent-frontend-return-conformance.md)
  - `examples/source_intent_frontend_conformance_gate.py`
  - `tests/golden/frontend/source_intent_frontend_conformance_gate.txt`

## Summary

Add a CI-facing Source Intent Frontend Conformance Gate that turns the reusable
frontend conformance suite into merge evidence.

## Motivation

Source Intent Frontend Conformance is the accepted path for external frontend
authors that emit `source_intent.v0` plain data. After RFC 0120 added explicit
public-return fixtures, CI should ensure those fixtures remain present instead
of only relying on the generic conformance report shape.

## Design

The gate builds the example Source Intent Frontend Conformance report and
requires:

- the conformance report passes
- at least one accepted and one rejected case are present
- the explicit public-return conformance cases are present:
  `valid_source_intent_return_mlp`,
  `reject_return_unknown_tensor`,
  `reject_return_intermediate_tensor`, and
  `reject_duplicate_public_returns`

The gate emits deterministic text evidence:

```text
source_intent.frontend_conformance_gate @source_intent_frontend_conformance_gate_v0
```

## Non-Goals

- changing the Source Intent Frontend Conformance report schema
- adding source parsing
- loading frontend packages from disk
- accepting preflight-to-intent conversion
- certifying executable backend plugins
- approving generated artifact execution

## Security

The gate checks bounded in-memory report metadata only. It does not read
frontend fixtures from paths, serialize raw payloads, include source text,
import frontend packages, discover plugins, access devices, use the network,
spawn subprocesses, execute generated artifacts, or run untrusted backend code.

## Acceptance Criteria

- Gate example emits deterministic PASS output.
- Golden output is checked in.
- Tests reject failed conformance reports.
- Tests reject reports missing required public-return conformance coverage.
- CI runs the gate.
- Full test suite remains green.
