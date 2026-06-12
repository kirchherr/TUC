# Source-To-Intent Parser Report

Source-To-Intent Parser Report v0 defines the deterministic report shape for
the first narrow parser proposal.

It is proposal-only evidence. It does not implement a parser.

The separate [Source-To-Intent Research Parser](SOURCE_TO_INTENT_RESEARCH_PARSER.md)
is the first explicit implementation slice. This report remains the proposal
golden that keeps the default parser path disabled.

## Contract

- Report contract: `source_to_intent_parser_report.proposal.v0`
- Report schema version: `tuc.source_to_intent_parser_report.v0`
- Example: `examples/source_to_intent_parser_report.py`
- Golden: `tests/golden/frontend/source_to_intent_parser_report.json`
- Tests: `tests/test_source_to_intent_parser_report.py`

## Current Status

```text
parser_status = proposal_only
implementation_status = not_implemented
parser_enabled = false
```

The report binds to:

- [Source-To-Intent Corpus Evidence](SOURCE_TO_INTENT_CORPUS.md)
- [Source-To-Intent Property Corpus](SOURCE_TO_INTENT_PROPERTY_CORPUS.md)

The only allowed future parser output is:

```text
source_intent.v0_plain_data_only
```

The current proposal report emits no parser outputs.

## Security Boundary

The report does not serialize raw source text, parser outputs,
`source_intent.v0` payloads, metadata, `ComputeGraph`, IR, runtime plans,
backend decisions, device handles, generated artifacts, subprocess output,
benchmark output, or raw compiler output.

It serializes only proposal metadata, corpus/report digests, counts, parser
disabled status, future output policy, and blocked execution/compiler-output
labels.

## Evidence

Run:

```bash
python examples/source_to_intent_parser_report.py
```

Expected result:

```text
parser_enabled = false
parser_status = proposal_only
implementation_status = not_implemented
```
