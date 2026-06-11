# RFC 0107: Runtime Graph Topology Contract v0

Status: Accepted

## Summary

Add a Runtime Executor preflight that validates graph topology before any
trusted prototype kernel executes.

## Motivation

Runtime Executor v0 already validates operation semantics, trusted backend
contracts, tensor values, and output contracts. It also needs an explicit graph
ordering contract so malformed graphs fail before partial execution.

Without this contract, a graph that reads a tensor before its producer could
degrade into a missing-value lookup, or a graph that redefines a tensor could
fail only after earlier operations already ran.

## Scope

Runtime Executor v0 now rejects:

- duplicate output tensor definitions
- inputs that read tensors produced by later operations
- operation outputs that overwrite external inputs

The check runs through execution readiness and `execute_graph`, before any
trusted kernel is called.

## Non-Goals

This RFC does not add:

- automatic graph sorting
- implicit repair of malformed graphs
- aliasing semantics
- in-place update semantics
- control flow
- side-effect modeling
- plugin or backend artifact execution

## Security Boundary

The topology contract is metadata-only. It reads `ComputeGraph` tensor names and
ordered operation structure. It does not inspect tensor values, discover
plugins, import modules, access devices, execute generated artifacts, spawn
subprocesses, touch the network, or load external files.

Malformed topology fails closed with deterministic diagnostics.

## Acceptance Criteria

- Valid proof graphs still execute unchanged.
- Read-before-produce graphs fail during readiness.
- Duplicate output definitions fail during readiness.
- External-input overwrite attempts fail during readiness.
- No new executable backend surface is introduced.
