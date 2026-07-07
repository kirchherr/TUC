# Source-To-Intent Next Syntax Slice

Source-To-Intent Next Syntax Slice v0 is the first broader parser-readiness
step after the initial explicit research parser.

It proves a narrow semantic mapping shape:

```text
branched Triton-like source buffer
  -> explicit research parser
  -> validated source_intent.v0 plain data
  -> semantic mapping report
  -> Source Intent golden digest
```

The slice is intentionally small. It covers branched dataflow, fanout value
reuse, all four current MVP operation families, and multiple terminal
`tl.store(...)` calls mapped to explicit public returns.

It does not enable direct Triton source ingestion, execute `@triton.jit`,
import Python modules, inspect Python function objects, access devices, create
metadata, build a `ComputeGraph`, or lower into runtime/backend artifacts.

## Contract

- Report schema: `schemas/source_to_intent_next_syntax_report.v0.schema.json`
- Report schema version: `tuc.source_to_intent_next_syntax_report.v0`
- Mapping contract: `source_to_intent_next_syntax.semantic_mapping.v0`
- RFC: `rfcs/0242-source-to-intent-next-syntax-slice.md`
- Example: `examples/source_to_intent_next_syntax_slice.py`
- Report golden: `tests/golden/frontend/source_to_intent_next_syntax_report.json`
- Source Intent golden:
  `tests/golden/frontend/source_to_intent_next_syntax_source_intent.json`
- Tests: `tests/test_source_to_intent_next_syntax_slice.py`

## Current Slice

The current accepted case is `next_syntax_branched_multi_return`.

It maps:

- `tl.dot(...)` to `matmul`;
- `tl.where(...)` to `elementwise`;
- `tl.softmax(..., axis=1)` to `softmax` with neutral `attributes.axis`;
- `tl.sum(..., axis=1)` to `reduction` with neutral `attributes.axis`;
- two terminal `tl.store(...)` calls to two explicit Source Intent public
  returns.

The semantic mapping report serializes only digest and count metadata. The
separate Source Intent golden serializes plain data only; it contains no raw
source text, host paths, devices, runtime handles, backend artifacts, generated
code, or plugin entrypoints.

## Readiness Meaning

This document satisfies four previously missing Triton Integration Readiness
prerequisites:

- broader parser implementation RFC;
- semantic mapping corpus for the next syntax;
- Source Intent goldens for the next syntax;
- fuzz/property coverage for semantic mapping.

It does not satisfy external frontend package conformance. The broader Triton
Integration Readiness report must therefore remain `not_ready`.

## Security Boundary

The slice remains behind the Source-To-Intent Parser Gate.

Future parser broadening must still fail closed on imports, decorator calls,
annotations, default arguments, host paths, devices, backend names, generated
artifacts, dynamic libraries, subprocesses, network access, plugins, raw
diagnostics, and source-to-`ComputeGraph` shortcuts.

The only allowed output of this slice is validated `source_intent.v0` plain
data plus metadata-only review evidence.
