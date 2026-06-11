# RFC 0104: Runtime Memory Planning Gate v0

Status: Accepted

## Summary

Add Runtime Memory Planning Gate v0 as a CI-facing composition of Runtime
Allocation Plan and Runtime Memory Budget evidence.

## Motivation

Runtime Allocation Plan v0 and Runtime Memory Budget v0 are useful only if they
stay enforced while the runtime grows. A small gate keeps the current memory
planning surface reviewable before real memory pools, aliasing, or device
allocation enter the project.

## Scope

This RFC adds:

- `examples/runtime_memory_planning_gate.py`
- `tests/golden/runtime_memory_planning_gate/current_gate.txt`
- `tests/test_runtime_memory_planning_gate.py`
- CI coverage in `.github/workflows/ci.yml`
- documentation in `docs/RUNTIME_MEMORY_PLANNING_GATE.md`

## Non-Goals

This RFC does not add:

- real memory allocation
- host or device capacity discovery
- memory pools
- device allocation
- alias analysis
- synchronization or stream overlap
- executable backend discovery
- performance claims

## Security Boundary

The gate consumes existing bounded data-only reports and checks that they pass
and refer to the same graph. It does not execute kernels, import backend
modules, load dynamic libraries, spawn subprocesses outside the example
process, read host paths, read environment variables, query devices, touch the
network, execute generated artifacts, or authorize executable backend surfaces.

## Acceptance Criteria

- The gate has deterministic golden output.
- The gate rejects failed allocation-plan evidence.
- The gate rejects failed memory-budget evidence.
- The gate rejects graph mismatches between the two reports.
- The gate is referenced in README, docs, roadmap status, and CI.
