# Source-To-Intent Research Parser Conformance Gate

Source-To-Intent Research Parser Conformance Gate v0 proves that the explicit
research parser output is accepted by the reusable Source Intent Frontend
Conformance suite.

It does not open the default source parser path.

## Contract

- Gate contract:
  `source_to_intent_research_parser_conformance_gate.ci.v0`
- Example:
  `examples/source_to_intent_research_parser_conformance_gate.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_parser_conformance_gate.txt`
- Tests:
  `tests/test_source_to_intent_research_parser_conformance_gate.py`
- CI entry: `.github/workflows/ci.yml`
- Related diagnostics:
  [Source-To-Intent Research Diagnostics](SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS.md)
- Research evidence gate:
  [Source-To-Intent Research Evidence Gate](SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md)

The gate passes only when:

- the explicit research parser report status remains `research_explicit_only`
- the default parser status remains `default_parser_blocked`
- parser output policy remains `source_intent.v0_plain_data_only`
- the parser-emitted `source_intent.v0` payload passes Source Intent Frontend
  Conformance
- required rejected payload cases fail closed at Source Intent Intake
- metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime-plan, and
  backend-decision outputs remain blocked at the parser report boundary

## Current Coverage

The gate binds both accepted parser slices to Source Intent Frontend
Conformance:

- `matmul -> elementwise`
- `softmax -> reduction`

The `softmax -> reduction` slice depends on the Source Intent `attributes.axis`
contract, which carries neutral axis semantics through Source Intent Intake and
Source Intent Metadata Conversion without introducing backend or device facts.

## Security Boundary

The gate consumes in-memory parser results and conformance reports. It does not
serialize raw source text, raw parser payloads, Python objects, file paths,
environment variables, generated code, plugin entrypoints, runtime tensors,
device handles, backend artifacts, or subprocess output.

The output is deterministic text ending in `PASS`.

## Review Meaning

This gate is merge-time evidence that the explicit research parser is not a
parallel frontend shortcut. Its output must survive Source Intent Intake,
Source Intent Metadata Conversion, graph construction, return/payload
validation, and neutral compiler planning through the reusable conformance
suite.

Source-To-Intent Research Diagnostics complements this gate by checking that
the same accepted parser scope and its rejected source cases produce stable,
source-free diagnostic evidence with whitelisted rejection reasons.

Source-To-Intent Research Evidence Gate binds this gate output to Research
Readiness and Research Diagnostics by SHA-256 digest.

It is not a production parser approval, native performance claim, plugin
certification runtime, or source-code execution path.
