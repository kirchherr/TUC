# RFC 0082: Runtime Backend Executor Contract

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha

## Summary

Add a pure-data contract for trusted in-process Runtime Executor backends.

The contract makes the fixed prototype executor registry inspectable without
turning Runtime Executor v0 into a plugin system or executable artifact loader.

## Motivation

Runtime Executor v0 can execute already-compiled graphs through trusted
in-repository prototype executors. The next practical boundary is to make each
executor's execution assumptions reviewable as data:

- which backend name is trusted
- which operation families it can execute
- which execution mode is allowed
- which input and output contracts apply
- which execution surfaces remain blocked

This is the stepping stone between proof-of-execution and future executable
backend proposals.

## Decision

Introduce `RuntimeBackendExecutorContract` with contract id:

```text
runtime_backend_executor.trusted.v0
```

Runtime Executor v0 accepts only:

```text
execution_mode = in_process_reference_kernel
external_artifacts = forbidden
device_access = forbidden
```

The contract's blocked execution surfaces must exactly match Runtime Executor
v0:

```text
backend_plugin_discovery
device_access
dynamic_import
dynamic_library_loading
generated_artifact_execution
jit_execution
network_access
subprocess_execution
```

Add deterministic contract golden evidence:

```text
tests/golden/runtime_backend_contracts/trusted_runtime_executor_registry.txt
```

## Security Model

This RFC does not add executable backend discovery, artifact execution, native
code loading, JIT execution, device access, subprocesses, dynamic imports,
dynamic libraries, network access, host-path reads, or environment-dependent
behavior.

The contract is produced from already trusted in-repository executors. It is not
parsed from external manifests in this RFC.

## Consequences

- The trusted prototype executor registry is reviewable as deterministic data.
- Future executable backend work has a named contract boundary to extend
  through a separate security RFC.
- Weakening the execution mode, artifact policy, device policy, or blocked
  execution-surface list fails closed in tests.

## References

- [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
- [Security Baseline](../docs/SECURITY_BASELINE.md)
- `src/tuc/runtime/executor.py`
- `tests/golden/runtime_backend_contracts/trusted_runtime_executor_registry.txt`
