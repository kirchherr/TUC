# Source-To-Intent Research Readiness

Source-To-Intent Research Readiness is a bounded evidence report for the first
real source parser research proposal.

It does not unblock source parsing. It records which evidence for the future
Source-to-Intent path already exists and which parser-specific artifacts remain
missing.

## Contract

- Gate contract: `source_to_intent_parser_gate.blocking.v0`
- Report schema version: `tuc.source_to_intent_readiness_report.v0`
- Example: `examples/source_to_intent_research_readiness.py`
- Golden: `tests/golden/frontend/source_to_intent_research_readiness.json`
- Tests: `tests/test_source_to_intent_research_readiness.py`

## Current Status

The research proposal remains blocked.

Current present evidence:

- parser RFC
- parser threat model update
- parser budget table
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

Current missing parser-specific evidence:

- accepted source corpus for source-to-intent semantics
- rejected source corpus for source-to-intent semantics
- source-to-intent parser fuzz or property corpus
- deterministic source-to-intent parser report golden

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

Expected status:

```text
ready = false
```

That blocked status is intentional until the missing parser-specific evidence
exists.
