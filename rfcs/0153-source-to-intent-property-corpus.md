# RFC 0153: Source-To-Intent Property Corpus

## Status

Accepted.

## Context

RFC 0152 added accepted and rejected source corpus evidence for the first
narrow Source-to-Intent parser proof. The research readiness report still
showed `source_fuzz_or_property_corpus` as missing.

Before parser logic can be accepted, TUC needs an explicit property corpus:
what arbitrary inputs, seed mutations, budget failures, diagnostics, execution
surfaces, and artifact boundaries a future parser must handle.

## Decision

Add Source-To-Intent Property Corpus evidence:

```text
examples/source_to_intent_property_corpus.py
tests/golden/frontend/source_to_intent_property_corpus_report.json
docs/SOURCE_TO_INTENT_PROPERTY_CORPUS.md
```

The report binds to Source-To-Intent Corpus Evidence by digest and records the
required parser properties:

```text
accepted_corpus_emits_only_source_intent_plain_data
arbitrary_decoded_bytes_fail_closed
diagnostics_are_bounded_and_source_free
forbidden_execution_surfaces_rejected
invalid_unicode_fail_closed
oversized_source_budget_fail_closed
rejected_corpus_never_emits_compiler_artifacts
seed_combinations_fail_closed
```

The research readiness example now marks `source_fuzz_or_property_corpus` as
present. Parser report golden evidence remains missing, so the parser is still
blocked.

## Security Boundary

This change does not add source parsing, fuzz execution against parser logic,
source-to-intent conversion, source-file loading as compiler input, Python
imports, decorator evaluation, `@triton.jit` execution, bytecode compilation,
frontend module inspection, plugin discovery, backend discovery, device access,
network access, subprocess execution, generated artifact execution, direct
`ComputeGraph` construction from source, or any source-to-metadata shortcut.

The property corpus report serializes only property IDs, categories,
expectations, source-corpus counts, a source-corpus report digest, raw-source
omission policy, and blocked execution/compiler-output labels.

## Consequences

TUC now has accepted source corpus, rejected source corpus, and parser
property-corpus evidence for the first narrow parser proof. RFC 0154 later adds
the proposal-only parser report golden and completes research-readiness
evidence while parser implementation remains disabled at that stage. RFC 0155
later adds the explicit research parser slice.
