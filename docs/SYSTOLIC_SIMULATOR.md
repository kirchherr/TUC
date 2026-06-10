# Systolic Simulator Proof

`systolic-sim` is TUC's second trusted in-process accelerator simulator.

It is a digital rank-2 matrix-multiplication simulator with a distinct
capability profile from `linear-sim`:

- backend name: `systolic-sim`
- supported operations: `matmul`
- preferred operations: `matmul`
- memory domain: `device_sram`
- supported input layout: `row_major`
- produced layout: `blocked`

The simulator is intentionally small. It proves that TUC can target another
accelerator class through capability data, runtime planning, readiness checks,
trusted execution, and golden evidence without making native performance
claims.

## Proof

Runnable proof:

```bash
python examples/proof_of_systolic_execution.py
```

The proof graph is:

```text
matmul -> elementwise
```

Runtime planning assigns:

- `systolic_projection` to `systolic-sim`
- `host_activation` to `reference-cpu`

The runtime plan records both the transfer from `device_sram` to `host_ram` and
the layout conversion from `blocked` to `row_major`.

## Evidence

- Proof golden: `tests/golden/proofs/proof_of_systolic_execution.txt`
- HAC-IR golden: `tests/golden/hac_ir/proof_of_systolic_execution.txt`
- Runtime-plan golden:
  `tests/golden/runtime_plans/proof_of_systolic_execution.txt`
- Compiler-decision golden:
  `tests/golden/compiler_decisions/proof_of_systolic_execution.txt`
- Execution-readiness golden:
  `tests/golden/execution_readiness/proof_of_systolic_execution.txt`
- Execution-trace golden:
  `tests/golden/execution_traces/proof_of_systolic_execution.txt`
- Runtime evidence matrix entry:
  `proof_of_systolic_execution`

## Security Boundary

`systolic-sim` does not discover plugins, import backend modules, spawn
subprocesses, access devices, load dynamic libraries, run JIT code, touch the
network, execute generated artifacts, or authorize external executable backend
artifacts.

Runtime execution still uses the trusted in-process Runtime Executor contract
and deterministic reference semantics.
