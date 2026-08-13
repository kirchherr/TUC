# RFC 0221: Backend Plugin Fuzz Negative Tests

Status: Accepted

## Context

RFC 0217 introduced Backend Plugin Lifecycle Policy as the blocking policy for
future executable backend plugin work. RFC 0218 accepted a data-only sandbox
model, RFC 0219 accepted digest-bound artifact provenance, and RFC 0220
accepted static resource-budget evidence.

At this RFC step, the next missing lifecycle requirement was fuzzing or
negative-test evidence.
Without a fail-closed negative-test inventory, future plugin proposals could
claim metadata is reviewed while malformed identifiers, oversized budgets,
duplicate records, invalid digests, or forbidden execution-surface keys are not
explicitly covered.

## Decision

Add Backend Plugin Fuzz Negative Tests v0 with:

- report model `src/tuc/backends/fuzz_negative_tests.py`;
- schema `schemas/backend_plugin_fuzz_negative_tests_report.v0.schema.json`;
- example `examples/backend_plugin_fuzz_negative_tests.py`;
- golden `tests/golden/backend_plugin_fuzz_negative_tests/current_report.json`;
- tests `tests/test_backend_plugin_fuzz_negative_tests.py`;
- negative-test contract `backend_plugin_fuzz_negative_tests.data_only.v0`.

The model records deterministic repository test coverage and seed identifiers
only:

```text
execution_permission = not_granted
execution_allowed = false
```

Each evidence case must bind to an accepted rejection class, deterministic seed
identifier, blocked execution surface, expected rejection result, and repository
evidence identifier. The report also binds to the accepted sandbox model,
artifact provenance, and resource budget contracts.

Backend Plugin Lifecycle Policy now treats `fuzz_negative_tests` as satisfied
by this accepted data-only evidence contract. The policy remains
execution-blocking after RFC 0222 accepts maintainer approval evidence.

## Security Boundary

The fuzz/negative-test report is data-only. It does not scan directories,
discover plugins, import modules, load dynamic libraries, execute generated
artifacts, access devices, spawn subprocesses, touch the network, inspect
environment variables, read host paths, load benchmark artifacts, read artifact
bytes, run fuzzers, or collect raw timing samples.

It records stable identifiers only. It does not record Python module names,
entry points, commands, device identifiers, source code, generated artifact
contents, native library paths, secrets, URLs, raw benchmark output, raw fuzz
corpus inputs, or artifact bytes.

## Consequences

TUC now has a concrete negative-test evidence layer for future executable
backend artifacts without opening a compiler execution surface.

Future plugin proposals still need an explicit implementation RFC before any
plugin discovery, artifact execution, native plugin ABI, dynamic-library
loading, device access, subprocess execution, network access, or JIT execution
can be enabled.
