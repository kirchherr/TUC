# RFC 0101: Runtime Buffer Lifetime

Status: accepted

## Summary

Add Runtime Buffer Lifetime v0 as a schema-versioned, deterministic report that
derives conservative produced tensor lifetimes and exact-match buffer reuse
candidates from a `ComputeGraph` and `PartitionPlan`.

## Motivation

TUC already explains backend assignment, transfer movement, layout conversion,
candidate scoring, and execution readiness. Future runtime planning also needs
memory-pressure evidence before it can discuss allocator behavior, buffer reuse,
or Von Neumann bottleneck mitigation in a concrete way.

This RFC adds the evidence surface without adding an allocator or executable
backend behavior.

## Artifacts

- [Runtime Buffer Lifetime](../docs/RUNTIME_BUFFER_LIFETIME.md)
- `schemas/runtime_buffer_lifetime_report.v0.schema.json`
- `examples/runtime_buffer_lifetime.py`
- deterministic golden:
  `tests/golden/runtime_buffer_lifetime/current_report.json`
- focused tests in `tests/test_runtime_buffer_lifetime.py`

## Design

The report computes one lifetime per produced tensor:

- producer operation and index
- first live index
- last use index
- last consumer or `graph_output`
- byte size
- memory domain and produced layout
- dtype and shape
- reuse group

Reuse groups are conservative. They require exact equality of memory domain,
layout, dtype, shape, and byte size. A tensor can reuse a group only when the
previous lifetime in that group has a strictly lower last-use index than the
new producer index.

The report also computes:

- total produced tensor bytes
- conservative peak live bytes
- reuse group count
- reuse savings upper bound

## Security

The report is data-only. It does not allocate memory, execute kernels, discover
plugins, import backend modules, load dynamic libraries, spawn subprocesses,
access devices, touch the network, execute generated artifacts, run JIT code,
read host paths, read environment variables, load raw benchmark output, or
approve executable backend surfaces.

All report fields are bounded. Issues are derived from the lifetimes and reuse
groups rather than accepted as arbitrary caller-provided text.

## Non-Goals

- No runtime allocator.
- No memory pool implementation.
- No in-place update semantics.
- No benchmark execution.
- No native performance claim.
- No executable backend approval.

## Acceptance

The RFC is accepted when:

- the example emits deterministic JSON,
- the report has a fail-closed schema,
- the golden output is covered by tests,
- negative tests cover forged issues and forbidden execution-surface text,
- roadmap and runtime documentation reference the report.

## Follow-Up

Future work may add explicit buffer allocation plans, aliasing policy, stream
synchronization evidence, and memory-pool simulation. Those changes must remain
inspectable and must not imply executable backend permission.
