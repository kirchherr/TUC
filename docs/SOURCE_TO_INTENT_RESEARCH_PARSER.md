# Source-To-Intent Research Parser

Source-To-Intent Research Parser v0 is the first explicit parser slice from a
caller-provided Triton-like source buffer into `source_intent.v0` plain data.

It is research evidence only. It is not a general Triton parser, not a compiler
input path, and not connected to metadata lowering unless a caller separately
passes the emitted plain data through the existing Source Intent Intake path.

## Contract

- Parser contract: `source_to_intent_research_parser.execution_free.v0`
- Report schema version: `tuc.source_to_intent_research_parser_report.v0`
- Report schema: `schemas/source_to_intent_research_parser_report.v0.schema.json`
- Status: `research_explicit_only`
- Default parser status: `default_parser_blocked`
- Output policy: `source_intent.v0_plain_data_only`
- Example: `examples/source_to_intent_research_parser.py`
- Golden: `tests/golden/frontend/source_to_intent_research_parser.json`
- Tests: `tests/test_source_to_intent_research_parser.py`

## Supported Slice

The current parser accepts only a tiny subset:

- one caller-provided source string
- one `@triton.jit`-decorated function, parsed as syntax data
- simple positional arguments only
- caller-provided tensor shapes for all function arguments
- `tl.dot(a, b)` as `matmul`
- `tl.where(...)` as `elementwise`
- `tl.softmax(x, axis=N)` as `softmax`
- `tl.sum(x, axis=N)` as `reduction`
- `tl.store(output_arg, produced_tensor)` as an explicit Source Intent public
  return alias

Everything else fails closed.

## Security Boundary

The parser runs `preflight_triton_source(...)` first, then uses `ast.parse`.
It does not import modules, evaluate decorators, execute `@triton.jit`, compile
bytecode, inspect Python functions, read source files by path, access devices,
touch the network, run subprocesses, load dynamic libraries, discover plugins,
write generated artifacts, or emit compiler artifacts.

The report serializes only metadata, source digest, counts, operation families,
blocked surfaces, and the validated Source Intent plain-data payload. It does
not serialize raw source text.

## Still Blocked

The default source parser path remains closed by
[Source-To-Intent Parser Block Gate](SOURCE_TO_INTENT_PARSER_BLOCK_GATE.md).

This parser does not change the blocked status of:

- arbitrary Triton syntax support
- `@triton.jit` execution
- source file ingestion by path
- Python module import
- source-to-metadata shortcuts
- source-to-`ComputeGraph` shortcuts
- source-to-HAC-IR shortcuts
- backend or device selection from source text

## Evidence

Run:

```bash
python examples/source_to_intent_research_parser.py
```

Expected report fields:

```text
parser_status = research_explicit_only
default_parser_status = default_parser_blocked
output_policy = source_intent.v0_plain_data_only
```
