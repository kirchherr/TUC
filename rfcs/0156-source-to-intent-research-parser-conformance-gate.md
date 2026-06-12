# RFC 0156: Source-To-Intent Research Parser Conformance Gate

## Status

Accepted.

## Context

RFC 0155 added the first explicit Source-to-Intent research parser slice. The
parser emits validated `source_intent.v0` plain data and remains disconnected
from metadata, `ComputeGraph`, IR, runtime planning, and backend decisions.

The next risk is parallel frontend drift: a parser could emit data that looks
valid locally but bypasses the reusable Source Intent Frontend Conformance path
used for external frontend authors.

## Decision

Add a CI-facing Source-To-Intent Research Parser Conformance Gate:

```text
source buffer
    ->
explicit research parser
    ->
source_intent.v0 plain data
    ->
Source Intent Frontend Conformance
    ->
PASS/FAIL gate report
```

The gate currently covers the `matmul -> elementwise` research parser slice and
requires rejected parser-shaped payloads for backend-hint and raw-source escape
attempts.

## Scope Boundary

The gate intentionally does not yet include the `softmax -> reduction` parser
slice. That parser path exists and is unit-tested, but Source Intent Metadata
Conversion does not yet carry axis attributes through Source Intent plain data.
Axis-carrying Source Intent metadata should be added through a separate RFC and
golden evidence before softmax/reduction enters this conformance gate.

## Security Constraints

The gate must not:

- import frontend packages
- execute source code
- evaluate decorators
- execute `@triton.jit`
- serialize raw source text
- serialize raw parser payloads
- emit metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, backend
  decisions, backend artifacts, or generated artifacts from the parser boundary

## Evidence

- Example:
  `examples/source_to_intent_research_parser_conformance_gate.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_parser_conformance_gate.txt`
- Tests:
  `tests/test_source_to_intent_research_parser_conformance_gate.py`
- Documentation:
  `docs/SOURCE_TO_INTENT_RESEARCH_PARSER_CONFORMANCE_GATE.md`
- CI:
  `.github/workflows/ci.yml`

## Consequences

TUC now proves that the first practical source-to-Source-Intent parser output is
not an isolated shortcut. It must pass the same reusable conformance path as an
external frontend author.

The default source parser path remains blocked.
