# RFC 0092: Systolic Simulator Proof

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha

## Summary

Add `systolic-sim` as a second trusted in-process accelerator simulator and add
a dedicated proof fixture that executes through the Runtime Executor.

## Motivation

TUC should not appear to be centered around one linear simulator plus a CPU
fallback. A second simulator with a different capability and layout profile
strengthens the Universal Compute claim while keeping the implementation
secure and inspectable.

## Decision

Add:

- `SystolicArraySimulatorBackend`
- trusted Runtime Executor entry `systolic-sim`
- `examples/proof_of_systolic_execution.py`
- [Systolic Simulator Proof](../docs/SYSTOLIC_SIMULATOR.md)
- proof, HAC-IR, runtime-plan, compiler-decision, readiness, and trace goldens
- Runtime Evidence Matrix coverage for `proof_of_systolic_execution`

`systolic-sim` supports only `matmul`, prefers `matmul`, uses `device_sram`,
accepts `row_major` input layout, and produces `blocked` output layout.

## Security Model

`systolic-sim` is a trusted in-process simulator. It does not discover plugins,
import backend modules, spawn subprocesses, access devices, load dynamic
libraries, run JIT code, touch the network, execute generated artifacts, or
authorize external executable backend artifacts.

Runtime execution still uses the existing trusted Runtime Executor contract and
deterministic reference semantics.

## Consequences

- TUC now has proof evidence for a second accelerator class.
- Runtime plans can show both memory-domain transfer and layout-conversion
  evidence from `device_sram`/`blocked` to `host_ram`/`row_major`.
- Runtime Executor Conformance now covers three trusted executors.
- Runtime Evidence Gate now covers six accepted graph fixtures.

## References

- [Systolic Simulator Proof](../docs/SYSTOLIC_SIMULATOR.md)
- [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
- [Runtime Evidence Matrix](../docs/RUNTIME_EVIDENCE_MATRIX.md)
- `examples/proof_of_systolic_execution.py`
- `tests/golden/proofs/proof_of_systolic_execution.txt`
