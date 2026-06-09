# RFC 0051: Triton Source Preflight Fuzz Corpus

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds property-test and seed-corpus coverage for the execution-free Triton
source preflight.

This RFC does not add source ingestion and does not connect source text to
metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, compiler decision
reports, or backend decisions.

## Motivation

RFC 0049 requires fuzzing or property-test coverage before any future Triton
source parser can accept untrusted source. RFC 0050 created the diagnostic
preflight boundary. The next gate is proving that this boundary handles
arbitrary decoded bytes, malformed syntax, seed combinations, invalid Unicode,
and diagnostic-volume pressure without throwing exceptions or exceeding report
budgets.

## Decision

Add `tests/test_triton_source_preflight_fuzz.py` and
`tests/corpus/triton_source_preflight/`.

The property tests cover:

- arbitrary byte sequences decoded with `surrogateescape`
- combinations of source corpus seeds
- invalid Unicode rejection
- bounded diagnostic count and diagnostic bytes
- preservation of blocked execution-surface evidence

The seed corpus covers:

- accepted `@triton.jit` syntax as data
- import rejection
- decorator-call rejection
- host-path literal rejection
- HAC-IR neutrality leakage rejection
- unsupported `tl.*` call rejection

## Consequences

- The preflight now has executable fuzz/property-test evidence.
- Source-intent IR remains blocked from lowering until it has its own RFC,
  corpus, goldens, and security review.
- RFC 0053 adds the Source Intent IR data model only; conversion to metadata or
  compiler artifacts remains blocked behind its own review gate.
- Future parser work can reuse this corpus as the first malformed-source seed
  set.

## Rejected Alternatives

1. Wait until a full source parser exists before adding fuzz coverage.

   Rejected because fuzzing should shape the boundary before source text can
   affect compiler artifacts.

2. Treat hand-written negative tests as enough.

   Rejected because arbitrary bytes, invalid Unicode, and seed combinations are
   more likely to reveal parser-boundary crashes than fixed examples alone.
