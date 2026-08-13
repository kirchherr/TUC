# RFC 0242: Source-To-Intent Next Syntax Slice

## Status

Accepted as parser-readiness evidence.

## Context

TUC has an explicit execution-free Source-To-Intent Research Parser for a tiny
Triton-like subset. The next roadmap concern is broader source credibility:
real parser growth must be prepared through semantic mapping evidence and
Source Intent goldens before any default source-ingestion path is opened.

The Triton Integration Readiness report therefore listed these missing
prerequisites:

- broader parser implementation RFC;
- semantic mapping corpus for the next syntax;
- Source Intent goldens for the next syntax;
- fuzz/property coverage for semantic mapping.

## Decision

Add a narrow next-syntax slice for branched multi-return source intent.

The slice accepts one explicit research-parser example with:

- branched symbolic dataflow;
- fanout reuse of one produced tensor;
- `tl.dot(...)` as `matmul`;
- `tl.where(...)` as `elementwise`;
- `tl.softmax(..., axis=1)` as `softmax`;
- `tl.sum(..., axis=1)` as `reduction`;
- multiple terminal `tl.store(...)` calls as explicit Source Intent public
  returns.

The slice emits:

- a metadata-only semantic mapping report;
- a deterministic Source Intent plain-data golden;
- property coverage for mapping invariants and blocked source execution
  surfaces.

## Security Constraints

This RFC does not allow default source ingestion.

The slice must not:

- import user modules;
- evaluate decorators;
- execute `@triton.jit`;
- compile Python bytecode;
- inspect Python function objects;
- read source files by path;
- access devices;
- access the network;
- run subprocesses;
- load dynamic libraries;
- discover plugins;
- emit metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, backend
  decisions, backend artifacts, generated artifacts, raw timing data, runtime
  handles, device identifiers, or host paths.

Every emitted Source Intent payload must pass `source_intent_from_mapping(...)`.
The semantic mapping report must serialize digests and bounded metadata only,
not raw source text.

## Evidence

- Implementation: `src/tuc/frontend/source_to_intent_next_syntax.py`
- Example: `examples/source_to_intent_next_syntax_slice.py`
- Report schema:
  `schemas/source_to_intent_next_syntax_report.v0.schema.json`
- Report golden:
  `tests/golden/frontend/source_to_intent_next_syntax_report.json`
- Source Intent golden:
  `tests/golden/frontend/source_to_intent_next_syntax_source_intent.json`
- Tests: `tests/test_source_to_intent_next_syntax_slice.py`
- Documentation: `docs/SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md`

## Consequences

TUC gains a broader source-to-intent proof slice without weakening the parser
gate. Triton Integration Readiness can mark the parser RFC, next-syntax
semantic mapping corpus, Source Intent goldens, and semantic mapping property
coverage as satisfied.

External frontend package conformance remains unsatisfied, so Real Triton
Integration remains `not_ready`.
