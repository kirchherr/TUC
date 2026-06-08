# RFC 0047: Triton Frontend Golden Artifacts

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Epsilon

## Summary

TUC adds deterministic golden artifacts for the Triton-like metadata frontend
path.

## Motivation

The Triton metadata intake contract proves that frontend input remains
execution-free. The next credibility step is to make the complete frontend path
reviewable from intake through compiler planning.

## Decision

Add golden fixtures for the `examples/triton_metadata_adapter.py` graph:

- `tests/golden/frontend/triton_metadata_intake.txt`
- `tests/golden/hac_ir/triton_metadata_mlp.txt`
- `tests/golden/runtime_plans/triton_metadata_mlp.txt`
- `tests/golden/compiler_decisions/triton_metadata_mlp.txt`

These fixtures are validated by
`tests/test_triton_frontend_golden_artifacts.py`.

## Security Model

The golden artifacts are generated from fixed in-repository metadata and
trusted in-memory capability data. The test path does not import user modules,
parse Python source, evaluate decorators, execute Triton JIT code, spawn
subprocesses, load dynamic libraries, access devices, touch the network, read
host paths, or execute generated artifacts.

## Consequences

- Triton-like frontend compatibility claims become inspectable.
- HAC-IR neutrality remains visible for frontend-originated graphs.
- Runtime fallback and backend support diagnostics remain reviewable before
  direct Triton source ingestion exists.

## Follow-Up

Future Triton idiom coverage should add or update frontend goldens only when it
introduces new compute-intent evidence. Direct `@triton.jit` handling remains blocked until a separate parser threat model, RFC, negative tests, and sandboxing plan exist.
