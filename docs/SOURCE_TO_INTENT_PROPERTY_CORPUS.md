# Source-To-Intent Property Corpus

Source-To-Intent Property Corpus v0 records fuzz/property obligations for the
narrow Source-to-Intent parser research path.

It is not a parser, not a fuzz runner, and not an ingestion path into Source
Intent IR or compiler artifacts.

## Contract

- Property contract: `source_to_intent_property_corpus.data_only.v0`
- Report schema version: `tuc.source_to_intent_property_corpus_report.v0`
- Example: `examples/source_to_intent_property_corpus.py`
- Golden: `tests/golden/frontend/source_to_intent_property_corpus_report.json`
- Tests: `tests/test_source_to_intent_property_corpus.py`

## Current Properties

The property corpus requires:

- accepted corpus emits only Source Intent plain data
- arbitrary decoded bytes fail closed or emit valid intent
- diagnostics remain bounded and source-free
- forbidden execution surfaces reject
- invalid Unicode fails closed
- oversized source budgets fail closed
- rejected corpus never emits compiler artifacts
- seed combinations fail closed or emit valid intent

The report is bound to
[Source-To-Intent Corpus Evidence](SOURCE_TO_INTENT_CORPUS.md) through a digest
of that data-only corpus report.

## Security Boundary

The report does not serialize raw source text, fuzz inputs, source paths,
Python objects, frontend modules, `source_intent.v0` payloads, metadata,
`ComputeGraph`, IR, runtime plans, backend decisions, device handles, generated
artifacts, subprocess output, benchmark output, or raw compiler output.

It serializes only property IDs, categories, expectations, corpus counts, a
source-corpus report digest, raw-source omission policy, and blocked
execution/compiler-output labels.

## Evidence

Run:

```bash
python examples/source_to_intent_property_corpus.py
```

Expected result:

```text
required_property_coverage_complete = true
raw_source_policy = omitted_by_policy
```
