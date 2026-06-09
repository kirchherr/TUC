# RFC 0056: Source Intent Intake Fuzz Corpus

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds property-test and seed-corpus coverage for Source Intent Intake.

This RFC does not add source parsing, preflight-to-intent conversion,
filesystem loading, metadata conversion, `ComputeGraph` construction, lowering,
runtime planning, backend selection, plugin discovery, or code execution.

## Motivation

RFC 0055 introduced schema-versioned plain-data intake for Source Intent IR. The
next security gate is proving that malformed JSON-like data, hostile keys, and
resource-shaped payloads either validate into bounded `SourceIntentModule`
objects or fail closed with `TypeError`/`ValueError`.

## Decision

Add `tests/test_source_intent_intake_fuzz.py` and
`tests/corpus/source_intent_intake/`.

The property tests cover:

- arbitrary JSON-like values
- seed payload wrapping
- valid seed intake
- unsupported schema versions
- source-text escape attempts
- backend-specific hint escape attempts
- unknown tensor references
- report evidence that source parsing, Python import, metadata output, and
  `ComputeGraph` output remain blocked

The seed corpus includes:

- `valid_mlp.json`
- `unsupported_schema.json`
- `source_text_escape.json`
- `backend_hint_escape.json`
- `unknown_tensor_reference.json`

## Consequences

- Source Intent Intake now has executable fuzz/property-test evidence.
- Future parser work can target the intake schema without weakening the intake
  boundary.
- Source text and preflight reports remain disconnected from Source Intent IR.

## Rejected Alternatives

1. Wait for a source parser before fuzzing Source Intent Intake.

   Rejected because malformed data handling should be proven before any parser
   emits data into the contract.

2. Treat fixed negative tests as enough.

   Rejected because property tests exercise broader plain-data shapes than a
   small hand-written corpus.

3. Add filesystem-based corpus loading to production intake.

   Rejected because the production API must remain path-free; corpus loading is
   test-only.
