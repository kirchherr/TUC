# RFC 0019: Backend Conformance Fixtures

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC adds reusable backend conformance fixtures for MVP operation lowering and
diagnostics.

## Motivation

Backend author certification now requires negative tests. The next step is a
positive/rejection fixture set that verifies a backend's declared capability data
matches lower-time behavior.

## Decision

Add `tuc.backends.conformance` with:

- `build_conformance_graph`
- `run_backend_conformance`
- `assert_backend_conformance`
- `BackendConformanceReport`
- `BackendConformanceIssue`

Add tests for:

- The reference simulator backend.
- Backend lowering of unsupported operations.
- Missing operation semantic markers in artifacts.
- Malformed diagnostics.
- Compact conformance error reporting.

## Security Model

The fixtures call only `backend.lower(graph)` on trusted in-process objects
constructed by tests. They do not discover plugins, import modules, read files,
spawn subprocesses, load dynamic libraries, access devices, or execute backend
artifacts.

Unsupported operation lowering is a conformance failure. Artifact and diagnostic
strings are bounded to avoid unbounded report growth.

## Consequences

- Backend contributors get copyable conformance tests.
- Maintainers get a consistent review signal for capability/lowering drift.
- TUC strengthens backend onboarding without opening a plugin surface.

## Follow-Up

1. Add numeric operation conformance once backend execution is sandboxed.
2. Add calibration and noise-model conformance when simulator semantics mature.
3. Add backend-specific golden artifacts only after artifact format contracts
   exist.
