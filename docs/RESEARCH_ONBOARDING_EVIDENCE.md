# Research Onboarding Evidence

Research Onboarding Evidence v0 makes the first public proof path reviewable as
bounded data. It is the executable companion to
`docs/RESEARCH_ONBOARDING_SLICE.md`.

Run it from the repository root:

```bash
python examples/research_onboarding_evidence.py
```

The report records:

- the Objective Alpha proof shape;
- the three fixed onboarding commands;
- the documentation path for each evidence step;
- blocked claims for native performance parity, vendor compiler replacement,
  broad source parsing, third-party backend execution, device access, and
  generated-artifact execution;
- the runtime executor's blocked execution surfaces;
- one metadata digest over the onboarding evidence contract.

## Security Boundary

This report is data-only. It does not execute the proof commands, parse source,
load manifests, discover plugins, access devices, run subprocesses, ingest
benchmark output, or execute generated artifacts.

All commands are fixed constants in TUC source. External text, paths, URLs,
host paths, raw tensor values, raw timing samples, plugin entrypoints, dynamic
libraries, and generated code are rejected by the report model or absent from
its schema.

## Schema And Golden

- Schema: `schemas/research_onboarding_report.v0.schema.json`
- Golden: `tests/golden/proofs/research_onboarding_report.json`
- Example: `examples/research_onboarding_evidence.py`
- Tests: `tests/test_research_onboarding_evidence.py`

## Non-Claims

The report does not claim native performance parity, broad production source
parsing, vendor compiler replacement, arbitrary backend execution, device
access, or generated-artifact execution.
