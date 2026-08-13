# Source Intent Axis Attributes

Source Intent Axis Attributes v0 define the only accepted neutral operation
attribute in `source_intent.v0`:

```text
attributes.axis
```

It is allowed only for `softmax` and `reduction`.

## Contract

- Plain-data key: `operations[*].attributes.axis`
- Accepted families: `softmax`, `reduction`
- Value type: bounded integer
- JSON Schema: `schemas/source_intent.v0.schema.json`
- Runtime intake: `source_intent_from_mapping(data)`
- Metadata conversion: `source_intent_to_triton_metadata(module)`
- Tests: `tests/test_source_intent_intake.py`,
  `tests/test_source_intent_metadata.py`,
  `tests/test_source_intent_schema.py`

## Semantics

`axis` is source intent, not backend placement. It describes which tensor axis
the source computation targets.

For `softmax`:

- one input tensor
- one output tensor
- output shape must match input shape
- axis must be in bounds

For `reduction`:

- one input tensor
- one output tensor
- output shape must equal input shape with the axis removed
- scalar reductions are not accepted in v0
- axis must be in bounds

## Security Boundary

No other operation attributes are accepted. In particular, Source Intent
attributes must not carry backend names, devices, memory domains, launch
configuration, paths, generated artifacts, plugin entrypoints, or `tuc.*`
reserved compiler facts.

`attributes.axis` may flow through Source Intent Metadata Conversion into
schema-versioned metadata because it is neutral mathematical intent. It must not
authorize execution, device access, backend selection, or runtime placement.

## Evidence

The axis contract allows the Source-To-Intent Research Parser Conformance Gate
to bind the `softmax -> reduction` parser output slice to Source Intent
Frontend Conformance.

```text
examples/source_to_intent_research_parser_conformance_gate.py
tests/golden/frontend/source_to_intent_research_parser_conformance_gate.txt
```
