# Source-To-Intent Research Evidence Gate

Source-To-Intent Research Evidence Gate v0 binds the current research parser
evidence chain by digest.

It does not open the default source parser path and does not authorize source
text as compiler input.

## Contract

- Gate contract: `source_to_intent_research_evidence_gate.ci.v0`
- Example: `examples/source_to_intent_research_evidence_gate.py`
- Execution bridge example:
  `examples/source_to_intent_research_execution_bridge.py`
- Execution bridge docs:
  [Source-To-Intent Research Execution Bridge](SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE.md)
- Golden: `tests/golden/frontend/source_to_intent_research_evidence_gate.txt`
- Tests: `tests/test_source_to_intent_research_evidence_gate.py`
- CI entry: `.github/workflows/ci.yml`

The gate binds:

- Source-To-Intent Research Readiness
- Source-To-Intent Research Parser Conformance Gate
- Source-To-Intent Research Diagnostics
- Source-To-Intent Research Execution Bridge

Each input artifact is hashed with SHA-256 and the digest is emitted in the
gate output.

## Required Checks

The gate passes only when:

- Research Readiness is `ready`.
- `SOURCE_TO_INTENT_REQUIRED_EVIDENCE` includes
  `source_to_intent_research_diagnostics`.
- Research Readiness marks both
  `source_intent_frontend_conformance_gate` and
  `source_to_intent_research_diagnostics` present.
- Research Parser Conformance Gate passes for the accepted parser sources.
- Research Diagnostics passes for the same accepted parser sources.
- Research Execution Bridge passes for the same accepted parser sources.
- Research Execution Bridge validates as a structured v0 contract before its
  digest is accepted.
- Diagnostics covers the whitelisted rejected source cases.
- Parser status remains `research_explicit_only`.
- Default parser status remains `default_parser_blocked`.
- Parser output policy remains `source_intent.v0_plain_data_only`.
- Metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime-plan, and
  backend-decision outputs remain blocked at the parser boundary.

## Security Boundary

The gate consumes already-rendered evidence or in-memory report objects. It
does not parse source text, import frontend modules from user code, evaluate
decorators, execute `@triton.jit`, read source files by path, access devices,
load plugins, run subprocesses, emit generated artifacts, or lower source text
to compiler artifacts.

The gate output is source-free. It must not contain raw source text, Source
Intent payloads, exception text, Python source snippets, device handles,
runtime tensors, host paths, environment variables, plugin entrypoints, or
subprocess output.

## Review Meaning

This gate makes the current parser research proof harder to drift:

```text
Research Readiness
    +
Research Parser Conformance Gate
    +
Research Diagnostics
    ->
Research Execution Bridge
    ->
Digest-bound source-free parser research evidence
```

Future parser syntax must update the diagnostics evidence, readiness evidence,
the execution bridge contract, and this gate before the expanded syntax can
count as accepted research parser scope.
