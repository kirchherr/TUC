# RFC 0155: Source-To-Intent Research Parser

## Status

Accepted as research evidence.

## Context

TUC must eventually show that real developer-facing source intent can reach the
hardware-independent interface. Prior evidence defined the parser gate, corpus,
property obligations, proposal-only parser report, and research readiness. The
remaining credibility gap was practical: source text still could not produce
validated Source Intent plain data.

## Decision

Add an explicit, execution-free research parser slice:

```text
caller-provided source buffer
    ->
Triton source preflight
    ->
Python AST as bounded syntax data
    ->
source_intent.v0 plain data
    ->
Source Intent Intake validation
```

The parser supports only:

- one function with simple positional arguments
- `tl.dot` -> `matmul`
- `tl.where` -> `elementwise`
- `tl.softmax(..., axis=N)` -> `softmax`
- `tl.sum(..., axis=N)` -> `reduction`
- `tl.store(output_arg, produced_tensor)` -> explicit Source Intent return

Tensor shapes come from a caller-provided plain-data shape manifest. The parser
does not infer shape facts from execution or host objects.

## Security Constraints

The parser must not:

- import user modules
- evaluate decorators
- execute `@triton.jit`
- compile bytecode
- inspect Python function objects
- read source files by path
- access devices
- access the network
- run subprocesses
- load dynamic libraries
- discover plugins
- emit metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, backend
  decisions, backend artifacts, or generated artifacts

Every emitted payload must pass `source_intent_from_mapping(...)`.

## Evidence

- Implementation: `src/tuc/frontend/source_to_intent_research_parser.py`
- Example: `examples/source_to_intent_research_parser.py`
- Report schema: `schemas/source_to_intent_research_parser_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_to_intent_research_parser.json`
- Tests: `tests/test_source_to_intent_research_parser.py`
- Documentation: `docs/SOURCE_TO_INTENT_RESEARCH_PARSER.md`

## Consequences

TUC now has a practical source-to-Source-Intent research proof without opening
the default source parser path.

This is not a production Triton parser and does not weaken the Source-To-Intent
Parser Block Gate. Broader syntax support requires new corpus cases,
properties, goldens, and review.
