# RFC 0154: Source-To-Intent Parser Report

## Status

Accepted.

## Context

RFC 0153 added property-corpus evidence and left only
`parser_report_golden` missing from the research readiness report.

The parser report must be handled carefully. Adding a golden must not imply
that TUC now implements source parsing or accepts source text as compiler input.

## Decision

Add Source-To-Intent Parser Report evidence:

```text
examples/source_to_intent_parser_report.py
tests/golden/frontend/source_to_intent_parser_report.json
docs/SOURCE_TO_INTENT_PARSER_REPORT.md
```

The report binds to Source-To-Intent Property Corpus evidence and records:

```text
parser_status = proposal_only
implementation_status = not_implemented
parser_enabled = false
allowed_future_output = source_intent.v0_plain_data_only
```

The research readiness example now marks `parser_report_golden` as present, so
the proposal evidence is complete. The default Source-To-Intent Parser Block
Gate remains unchanged and continues to prove the ordinary parser path is
closed.

## Security Boundary

This change does not add source parsing, source-to-intent conversion, source
file loading as compiler input, Python imports, decorator evaluation,
`@triton.jit` execution, bytecode compilation, frontend module inspection,
plugin discovery, backend discovery, device access, network access, subprocess
execution, generated artifact execution, direct `ComputeGraph` construction
from source, or any source-to-metadata shortcut.

The parser report serializes only proposal metadata, corpus/report digests,
counts, parser disabled status, future output policy, and blocked
execution/compiler-output labels.

## Consequences

TUC now has a complete proposal-evidence set for the first narrow
Source-to-Intent parser proof. The next step is not to open the default parser
path; it is to decide, through a dedicated implementation RFC, whether a
minimal parser implementation may target this report and the existing corpus
contracts.

RFC 0155 accepts that next step as an explicit research parser slice while
keeping the default parser path closed.
