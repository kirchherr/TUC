# RFC 0160: Source-To-Intent Research Execution Bridge

## Status

Accepted.

## Context

The explicit Source-to-Intent research parser has conformance, diagnostics,
and digest-bound evidence. The next practical proof step is showing that
accepted parser output can reach controlled runtime execution without turning
the parser into a compiler shortcut.

## Decision

Add Source-To-Intent Research Execution Bridge v0.

The bridge takes accepted in-memory research parser results and re-enters the
normal frontend path through `source_intent_from_mapping(...)`. It then uses
Source Intent Metadata Conversion, normal graph construction, compilation,
Runtime Execution Readiness, Runtime Executor, and Runtime Reference
Correctness.

The report is metadata-only and records digests for the accepted execution
path instead of raw values.

## Security Constraints

The bridge must not:

- read source files by path
- serialize raw source text
- serialize raw Source Intent payloads
- serialize raw tensor values
- import user modules
- evaluate decorators
- execute `@triton.jit`
- compile bytecode
- discover plugins
- access devices
- run subprocesses
- load dynamic libraries
- execute generated artifacts
- let parser output directly produce metadata, `ComputeGraph`, TLIR, HAC-IR,
  HS-IR, runtime plans, or backend decisions

All compiler artifacts in the bridge are produced only after explicit Source
Intent Intake accepts already emitted `source_intent.v0` plain data.

## Evidence

- Bridge: `examples/source_to_intent_research_execution_bridge.py`
- Documentation: `docs/SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE.md`
- Schema:
  `schemas/source_to_intent_research_execution_bridge_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/source_to_intent_research_execution_bridge.json`
- Tests: `tests/test_source_to_intent_research_execution_bridge.py`
- CI: `.github/workflows/ci.yml`
- Digest binding: `examples/source_to_intent_research_evidence_gate.py`

## Consequences

The accepted parser research scope now has practical runtime evidence. This
does not approve default source ingestion or a production parser; it proves
that explicitly accepted parser output can travel through the existing audited
TUC path into controlled execution.
