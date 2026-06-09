# RFC 0048: Triton MVP Metadata Coverage

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds a Triton-like metadata example that covers every current MVP operation
family in one frontend-originated graph.

## Motivation

The first Triton metadata golden path proved that schema-versioned frontend
intake is execution-free and reviewable. It covered `matmul` and `elementwise`.
Phase Epsilon also needs frontend-originated evidence for `softmax` and
`reduction` before direct Triton syntax or `@triton.jit` handling can be
considered.

## Decision

Add `examples/triton_mvp_metadata.py`.

The graph is:

```text
matmul -> softmax -> matmul -> reduction -> elementwise
```

It uses schema-versioned `triton_metadata.v0` metadata, validates against
deterministic reference kernels, and emits a runtime plan that makes linear
simulator assignments, fallback assignments, and cross-domain transfer bytes
visible.

Add golden artifacts:

- `tests/golden/frontend/triton_metadata_mvp_families_intake.txt`
- `tests/golden/hac_ir/triton_metadata_mvp_families.txt`
- `tests/golden/runtime_plans/triton_metadata_mvp_families.txt`
- `tests/golden/compiler_decisions/triton_metadata_mvp_families.txt`

## Security Model

The example uses fixed in-repository metadata and deterministic in-memory
reference inputs. It does not parse Python source, import user modules, execute
Triton JIT code, spawn subprocesses, load dynamic libraries, access devices,
touch the network, read host paths, or execute generated artifacts.

## Consequences

- Phase Epsilon has frontend-originated coverage for all MVP operation
  families.
- Softmax remains a single operation-family intent in HAC-IR; decomposition is
  still blocked by the softmax planning contract.
- Backend support and fallback evidence remain visible in compiler decision
  reports.

## Follow-Up

Future Triton idiom coverage should add new metadata examples only when they
introduce new compute-intent evidence. Direct Triton source ingestion remains blocked until a parser threat model, RFC, fuzzing plan, negative tests, and sandboxing model exist.
