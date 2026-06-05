# RFC 0009: Runtime Plan Golden Dumps

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1

## Summary

TUC adds runtime-plan golden dump fixtures for representative transfer,
layout-conversion, and calibrated-profile scenarios. These fixtures lock the
human-readable runtime plan format while the partitioner is still intentionally
simple.

## Motivation

Runtime partitioning is becoming a compiler contract, not only a helper
function. As TUC adds memory-domain transfers, produced layouts, layout
conversions, and transfer-cost profiles, small dump regressions can hide
behavioral changes that future backend authors and reviewers need to see.

Golden dumps give maintainers stable artifacts for reviewing those changes.

## Decision

Add static fixture files under `tests/golden/runtime_plans/` and compare them
against `dump_partition_plan(...)` output in unit tests.

The initial fixture set covers:

- Default analog-to-GPU transfer cost estimation.
- Backend-produced layout causing followup layout conversion.
- Calibrated transfer-cost profile output.

## Security Model

Golden tests do not execute generators, backend plugin code, subprocesses, or
external files. They construct typed in-memory graphs and compare deterministic
text output against repository-owned fixtures.

The fixtures are reviewable plain text. Any future fixture update should be
treated as a visible compiler-contract change.

## Consequences

- Runtime plan dump changes now require intentional fixture updates.
- Reviewers can see exact assignment, transfer, produced-layout, conversion,
  latency, and energy output.
- This supports future backend API work without adding runtime complexity.

## Follow-Up

1. Add golden dumps for frontend-adapter-generated graphs.
2. Add benchmark result fixtures only after benchmark methodology is defined.
3. Add serialized IR golden tests once serialization exists.
