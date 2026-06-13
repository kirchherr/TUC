# RFC 0157: Source Intent Axis Attributes

## Status

Accepted.

## Context

The explicit Source-to-Intent research parser can parse `softmax` and
`reduction` source patterns with explicit axis syntax. Before this RFC, Source
Intent plain data had no neutral operation-attribute channel, so axis semantics
could not flow through Source Intent Metadata Conversion into the reusable
Frontend Conformance path.

Without this contract, the parser could prove syntax handling but not
end-to-end Source Intent conformance for `softmax -> reduction`.

## Decision

Add a narrow Source Intent operation attribute contract:

```text
operations[*].attributes.axis
```

The attribute is allowed only for `softmax` and `reduction`. It is an integer
validated against input rank and output shape during Source Intent Intake.

Source Intent Metadata Conversion forwards this neutral attribute to
schema-versioned metadata operation attributes.

## Security Constraints

The attribute map must remain closed:

- no backend names
- no devices
- no memory domains
- no placement
- no launch configuration
- no paths
- no generated artifacts
- no plugin entrypoints
- no `tuc.*` reserved compiler facts
- no arbitrary attribute names

`axis` is mathematical source intent only. It must not authorize execution,
backend selection, device access, or runtime placement.

## Evidence

- Runtime model: `src/tuc/frontend/source_intent.py`
- Plain-data intake: `src/tuc/frontend/source_intent_intake.py`
- Metadata conversion: `src/tuc/frontend/source_intent_metadata.py`
- JSON Schema: `schemas/source_intent.v0.schema.json`
- Documentation: `docs/SOURCE_INTENT_AXIS_ATTRIBUTES.md`
- Parser conformance gate:
  `examples/source_to_intent_research_parser_conformance_gate.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_parser_conformance_gate.txt`
- Tests:
  `tests/test_source_intent_intake.py`,
  `tests/test_source_intent_metadata.py`,
  `tests/test_source_intent_schema.py`,
  `tests/test_source_to_intent_research_parser.py`,
  `tests/test_source_to_intent_research_parser_conformance_gate.py`

## Consequences

TUC can now bind the `softmax -> reduction` parser output slice to the same
Source Intent Frontend Conformance path as `matmul -> elementwise`.

Broader operation attributes remain blocked until separately specified,
schema-versioned, documented, and golden-tested.
