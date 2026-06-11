# RFC 0118: Source Intent Runtime Returns Gate Coverage

- Status: Accepted
- Related:
  - [Source Intent Runtime Returns](../docs/SOURCE_INTENT_RUNTIME_RETURNS.md)
  - [Runtime Evidence Matrix](../docs/RUNTIME_EVIDENCE_MATRIX.md)
  - [Runtime Evidence Gate](../docs/RUNTIME_EVIDENCE_GATE.md)
  - `schemas/source_intent_runtime_returns_report.v0.schema.json`
  - `tests/golden/frontend/source_intent_runtime_returns_report.json`
  - `tests/golden/proofs/runtime_evidence_matrix_report.json`
  - `tests/golden/proofs/runtime_evidence_gate.txt`

## Summary

Add Source Intent Runtime Returns to the curated Runtime Evidence Matrix and
require the report in the CI-facing Runtime Evidence Gate.

## Motivation

Source Intent Runtime Returns v0 proves that explicit frontend return intent can
resolve through Runtime Output Contract and Runtime Public Output Bundle. If
that proof stays outside the evidence gate, TUC can accidentally regress the
frontend-to-runtime return path while the general runtime gate still passes.

## Design

Runtime Evidence Matrix now includes:

- artifact kind `source_intent_return_semantics`
- artifact kind `source_intent_runtime_returns`
- graph fixture `source_intent_return_mlp`

The new graph remains complete under the existing required runtime evidence
kinds and additionally records Source Intent-specific return evidence.

Runtime Evidence Gate now also builds and checks Source Intent Runtime Returns
evidence. The gate still does not scan the repository, load plugins, parse
source, or serialize tensor values.

## Non-Goals

- making Source Intent return evidence required for non-Source-Intent graphs
- changing runtime execution semantics
- enabling source-text parsing
- adding positional return semantics
- adding executable backend discovery

## Security

The additional gate input is the existing metadata-only
`SourceIntentRuntimeReturnsReport`. It contains contract identifiers, public
names, tensor names, digests, and blocked surfaces only. Raw tensor values,
source text, paths, device identifiers, generated code, subprocesses, and
network locations remain excluded.

## Acceptance Criteria

- Runtime Evidence Matrix golden includes `source_intent_return_mlp`.
- Matrix schema allows Source Intent return artifact kinds.
- Runtime Evidence Gate fails without a valid Source Intent Runtime Returns
  report.
- Runtime Evidence Gate golden reports Source Intent Runtime Returns as passed.
- Full test suite remains green.
