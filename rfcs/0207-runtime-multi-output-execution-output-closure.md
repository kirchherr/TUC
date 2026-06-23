# RFC 0207: Runtime Multi-Output Execution Output Closure

Status: Accepted

## Context

Runtime Execution Output Closure v0 first proved the public output boundary for
the single-output proof-of-execution fixture. TUC also has a multi-output
runtime fixture with explicit public aliases, read-only public output bundle
values, and independent reference correctness for two terminal outputs.

## Decision

Add a multi-output Runtime Execution Output Closure fixture:

- `examples/runtime_multi_output_execution_output_closure.py`
- `tests/golden/runtime_execution_output_closure/multi_output_execution.json`
- `tests/test_runtime_multi_output_execution_output_closure.py`

The fixture composes the existing trusted Runtime Executor, Tensor Store
Evidence, Input Manifest, Output Manifest, Runtime Output Contract, Runtime
Public Output Bundle, Reference Correctness, Execution Receipt, Execution
Evidence Bundle, and Output Closure builders for `multi_output_execution`.

## Security Boundary

The fixture is metadata-only and uses the fixed trusted in-repository simulator
backend path. It does not serialize tensor values, source text, host paths,
commands, backend artifacts, device identifiers, timing samples, runtime
handles, URLs, or plugin entry points.

## Consequences

Output closure now covers both a single-output proof path and a two-public-output
runtime path. This strengthens the Universal Compute evidence without adding
native performance, broad source parsing, vendor replacement, device-access,
or generated-artifact execution claims.
