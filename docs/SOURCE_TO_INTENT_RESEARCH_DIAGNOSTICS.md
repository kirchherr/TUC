# Source-To-Intent Research Diagnostics

Source-To-Intent Research Diagnostics v0 is deterministic evidence for the
explicit research parser's accepted and rejected source-buffer cases.

It is not a general parser approval and does not open the default source parser
path.

## Contract

- Diagnostics contract:
  `source_to_intent_research_diagnostics.execution_free.v0`
- Report schema version:
  `tuc.source_to_intent_research_diagnostics_report.v0`
- Report schema:
  `schemas/source_to_intent_research_diagnostics_report.v0.schema.json`
- Raw source policy: `omitted_by_policy`
- Parser status: `research_explicit_only`
- Default parser status: `default_parser_blocked`
- Output policy: `source_intent.v0_plain_data_only`
- Example: `examples/source_to_intent_research_diagnostics.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_diagnostics_report.json`
- Tests: `tests/test_source_to_intent_research_diagnostics.py`
- CI entry: `.github/workflows/ci.yml`
- Evidence gate:
  [Source-To-Intent Research Evidence Gate](SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md)
- Evidence gate example:
  `examples/source_to_intent_research_evidence_gate.py`

## What It Proves

The report runs the explicit research parser against the accepted and rejected
source cases that define the current narrow parser proof.

Accepted cases must produce parser reports with safe metadata:

- source digest
- source byte count
- operation families
- parser report digest
- parser status and output policy

Rejected cases must fail closed with an expected whitelisted rejection reason:

- `missing_axis_keyword`
- `preflight_decorator_call`
- `preflight_import_statement`
- `unsupported_assignment_value`

The report contains no raw source text, Source Intent payloads, metadata,
`ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, backend decisions, runtime
tensors, generated artifacts, exception text, or subprocess output.

## Security Boundary

The diagnostics builder calls only
`parse_triton_source_to_source_intent(...)` with caller-provided source buffers
and caller-provided shape manifests. It does not read files by path, import
frontend modules from source, evaluate decorators, execute `@triton.jit`,
inspect Python functions, load plugins, access devices, run subprocesses, or
emit executable artifacts.

Rejection messages are not serialized. The report stores only stable
source-free reason IDs, which prevents accidental leakage of source snippets,
host paths, or environment details.

## Review Meaning

This evidence strengthens the parser research boundary by making negative
coverage reviewable. It shows that the current accepted parser slice is small,
that known hostile or unsupported source forms stay rejected, and that parser
diagnostics remain source-free and bounded.

The Source-To-Intent Research Evidence Gate binds this diagnostics report to
Research Readiness and the Research Parser Conformance Gate by SHA-256 digest.

Future parser syntax must add its own Source Intent semantic contract and
extend this diagnostics report before it can be treated as accepted parser
evidence.
