# RFC 0158: Source-To-Intent Research Diagnostics

## Status

Accepted.

## Context

The explicit Source-to-Intent research parser now covers two narrow accepted
source slices:

- `matmul -> elementwise`
- `softmax -> reduction`

The second slice depends on the neutral Source Intent `attributes.axis`
contract. Before expanding parser syntax further, the project needs stronger
evidence that the accepted scope and rejected source cases remain stable,
bounded, and source-free.

This responds to the central frontend risk: real parser work can become a
leaky shortcut into compiler artifacts if diagnostics, negative cases, and
accepted scope are not made reviewable.

## Decision

Add Source-To-Intent Research Diagnostics v0.

The diagnostics report runs the explicit research parser against accepted and
rejected source-buffer cases and emits only:

- case IDs
- source digests
- source byte counts
- accepted operation families
- accepted parser report digests
- whitelisted rejection reason IDs
- parser status and blocked-surface policy

The report does not serialize raw source text, Source Intent payloads,
metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, backend
decisions, exception text, runtime tensors, generated artifacts, or subprocess
output.

## Security Constraints

Rejection reasons must be stable IDs from an allowlist. Raw exception text is
used only internally to match the expected rejection and is never written to
the report.

The diagnostics path must not add:

- file-path source ingestion
- Python imports
- decorator evaluation
- `@triton.jit` execution
- bytecode compilation
- device access
- network access
- subprocess execution
- plugin discovery
- generated artifact execution
- source-to-metadata, source-to-graph, source-to-IR, or source-to-runtime-plan
  shortcuts

## Evidence

- Runtime model:
  `src/tuc/frontend/source_to_intent_research_diagnostics.py`
- Example:
  `examples/source_to_intent_research_diagnostics.py`
- JSON Schema:
  `schemas/source_to_intent_research_diagnostics_report.v0.schema.json`
- Documentation:
  `docs/SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS.md`
- Golden:
  `tests/golden/frontend/source_to_intent_research_diagnostics_report.json`
- Tests:
  `tests/test_source_to_intent_research_diagnostics.py`
- CI:
  `.github/workflows/ci.yml`

## Consequences

The research parser now has source-free negative evidence alongside
conformance evidence. Future parser syntax must extend diagnostics before it
can be treated as accepted research parser scope.

This does not approve a production parser or default source compiler input
path.
