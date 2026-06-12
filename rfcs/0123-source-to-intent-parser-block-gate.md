# RFC 0123: Source-To-Intent Parser Block Gate

- Status: Accepted
- Related:
  - [Source-To-Intent Parser Gate](../docs/SOURCE_TO_INTENT_PARSER_GATE.md)
  - [Source-To-Intent Readiness Report](../docs/SOURCE_TO_INTENT_READINESS.md)
  - [Source-To-Intent Parser Block Gate](../docs/SOURCE_TO_INTENT_PARSER_BLOCK_GATE.md)
  - [RFC 0122](0122-source-to-intent-readiness-frontend-gate.md)
  - `examples/source_to_intent_parser_block_gate.py`
  - `tests/golden/frontend/source_to_intent_parser_block_gate.txt`

## Summary

Add a CI-facing Source-To-Intent Parser Block Gate that passes only while the
default source-to-intent parser state remains intentionally blocked.

## Motivation

TUC has strong prose and readiness evidence saying source text must not
influence compiler artifacts yet. That blocked state should also be merge-time
evidence, so accidental parser readiness claims or partial evidence changes
cannot slip through as a harmless report update.

## Design

The gate builds the default blocked Source-To-Intent Readiness report and
requires:

- readiness is not ready
- checked evidence IDs match `SOURCE_TO_INTENT_REQUIRED_EVIDENCE`
- every required evidence item is missing in the default blocked report
- `source_intent_frontend_conformance_gate` is among the missing evidence
- blocked execution surfaces match the Source-To-Intent parser gate contract

The gate emits deterministic text evidence:

```text
source_to_intent.parser_block_gate @source_to_intent_parser_block_gate_v0
```

## Non-Goals

- implementing a source parser
- accepting source text as compiler input
- validating source parser payload semantics
- changing Source-To-Intent Readiness schema version
- loading frontend packages or executing generated artifacts

## Security

The gate consumes bounded in-memory readiness metadata only. It does not parse
source text, inspect preflight reports, load source files, serialize raw
payloads, import frontend modules, discover plugins, access devices, use the
network, spawn subprocesses, execute generated artifacts, or run backend code.

## Acceptance Criteria

- Gate example emits deterministic PASS output.
- Golden output is checked in.
- Tests reject unexpectedly ready parser-readiness reports.
- Tests reject changed default blocked evidence.
- CI runs the gate.
- Full test suite remains green.
