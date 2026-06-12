# Source-To-Intent Corpus Evidence

Source-To-Intent Corpus Evidence v0 inventories the first accepted and rejected
source buffers for the narrow parser research path.

It is not a parser and does not create `source_intent.v0` payloads.

## Contract

- Corpus contract: `source_to_intent_corpus.data_only.v0`
- Report schema version: `tuc.source_to_intent_corpus_report.v0`
- Example: `examples/source_to_intent_corpus.py`
- Golden: `tests/golden/frontend/source_to_intent_corpus_report.json`
- Fixtures: `tests/corpus/source_to_intent_parser/`
- Tests: `tests/test_source_to_intent_corpus.py`

## Current Corpus

Accepted source buffers:

- `accepted_matmul_elementwise`
- `accepted_softmax_reduction`

Rejected source buffers:

- `reject_ambiguous_softmax_axis`
- `reject_decorator_call`
- `reject_hardware_hint`
- `reject_import_escape`

The accepted cases cover the MVP operation families:

```text
elementwise,matmul,reduction,softmax
```

## Security Boundary

The report does not serialize raw source text, source paths, Python objects,
frontend modules, `source_intent.v0` payloads, metadata, `ComputeGraph`, IR,
runtime plans, backend decisions, device handles, generated artifacts, or raw
compiler output.

It serializes only case IDs, accepted/rejected expectations, byte counts,
source digests, operation-family labels, expected rejection labels, and blocked
execution/compiler-output labels.

The corpus defines parser obligations and seeds the explicit research parser
slice, but it must not let source text influence compiler artifacts directly.

## Evidence

Run:

```bash
python examples/source_to_intent_corpus.py
```

Expected result:

```text
mvp_operation_family_coverage_complete = true
accepted_case_count = 2
rejected_case_count = 4
```
