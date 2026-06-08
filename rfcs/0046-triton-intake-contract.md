# RFC 0046: Triton Metadata Intake Contract

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Epsilon

## Summary

TUC hardens the Triton-like metadata adapter with a schema-versioned intake
contract and deterministic intake reports.

## Motivation

Phase Epsilon needs a credible path from Triton-style developer intent into
HAC-IR. Directly parsing Python source or executing `@triton.jit` functions
would introduce imports, decorators, bytecode, device assumptions, and JIT
execution before TUC has a parser threat model or sandbox.

The next safe step is to make the existing metadata boundary explicit and
reviewable.

## Decision

Add:

- `TRITON_METADATA_SCHEMA_VERSION = "triton_metadata.v0"`
- `TRITON_METADATA_INTAKE_CONTRACT = "triton_intake.execution_free.v0"`
- `TritonIntakeReport`
- `TritonKernelMetadata.intake_report()`

The adapter accepts an optional `schema_version` field. Missing schema versions
default to `triton_metadata.v0`; unsupported versions fail closed.

The produced `ComputeGraph` records:

- `frontend.adapter`
- `frontend.schema_version`
- `frontend.intake_contract`

## Security Model

The intake contract is data-only:

- no Python imports
- no Triton JIT execution
- no bytecode inspection
- no subprocesses
- no dynamic libraries
- no device access
- no network access
- no generated-artifact execution

Known execution-surface keys such as `import_module`, `python_source`,
`jit_function`, `dynamic_library`, `device_path`, `subprocess`, `url`, and
`generated_artifact` are rejected from graph metadata and operation attributes
even when those containers are otherwise allowed.

## Consequences

- TUC can claim a stronger L3 Triton adapter contract.
- Future Triton idiom coverage has a safe entry point.
- Direct source parsing and `@triton.jit` handling remain future work requiring
  a dedicated threat model, RFC, negative tests, and sandboxing plan.

## Validation

Tests cover:

- accepted schema-versioned metadata
- deterministic intake report output
- unsupported schema rejection
- execution-surface rejection in graph metadata
- execution-surface rejection in operation attributes
- pipeline compilation through TLIR, HAC-IR, HS-IR, and runtime planning
