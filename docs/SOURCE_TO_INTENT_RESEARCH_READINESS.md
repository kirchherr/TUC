# Source-To-Intent Research Readiness

Source-To-Intent Research Readiness is a bounded evidence report for the first
real source parser research proposal.

It does not unblock source parsing. It records whether the proposal evidence
for the future Source-to-Intent path exists.

## Contract

- Gate contract: `source_to_intent_parser_gate.blocking.v0`
- Report schema version: `tuc.source_to_intent_readiness_report.v0`
- Example: `examples/source_to_intent_research_readiness.py`
- Golden: `tests/golden/frontend/source_to_intent_research_readiness.json`
- Tests: `tests/test_source_to_intent_research_readiness.py`

## Current Status

The research proposal evidence is complete.

This means the proposal has all required review artifacts. A first explicit
research parser slice now exists, but it is not enabled as a default compiler
input path.

Current present evidence:

- accepted source corpus
- parser RFC
- parser threat model update
- parser budget table
- deterministic source-to-intent parser report golden
- rejected source corpus
- source-to-intent parser fuzz or property corpus
- Source Intent plain-data golden
- Source Intent Intake report golden
- Source Intent Metadata Conversion report golden
- metadata intake report golden
- HAC-IR golden
- runtime-plan golden
- compiler decision-report golden
- HAC-IR neutrality review
- Source Intent Frontend Conformance report
- Source Intent Frontend Conformance Gate output

## Research Boundary

This report exists because TUC is a research project proving that a
hardware-independent compute interface can be made explicit, auditable, and
secure by design. It is not a claim that TUC replaces CUDA, ROCm, XLA, TVM, or
production vendor compilers.

The first source parser must remain narrow: caller-provided source buffer,
bounded syntax data, emitted `source_intent.v0` plain data, Source Intent
Intake, metadata conversion, then ordinary TUC graph compilation. It must not
import user modules, evaluate decorators, execute `@triton.jit`, produce
`ComputeGraph` directly, or smuggle backend/device placement into Source
Intent IR.

## Evidence

Run:

```bash
python examples/source_to_intent_research_readiness.py
```

Corpus evidence:

```bash
python examples/source_to_intent_corpus.py
```

Property corpus evidence:

```bash
python examples/source_to_intent_property_corpus.py
```

Parser report evidence:

```bash
python examples/source_to_intent_parser_report.py
```

Explicit research parser evidence:

```bash
python examples/source_to_intent_research_parser.py
```

Expected status:

```text
ready = true
```

That ready status means proposal evidence is complete. The default parser path
remains closed by the Source-To-Intent Parser Block Gate, the proposal parser
report still says `parser_enabled = false`, and the explicit research parser is
limited to `source_intent.v0` plain-data output.
