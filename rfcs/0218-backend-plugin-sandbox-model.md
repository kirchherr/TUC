# RFC 0218: Backend Plugin Sandbox Model

Status: Accepted

## Context

RFC 0217 introduced Backend Plugin Lifecycle Policy as the blocking policy for
future executable backend plugin work. That policy deliberately kept plugin
discovery, generated artifact execution, and native plugin ABI loading disabled
until several requirements exist.

The highest-risk missing requirement is the sandbox model. Without it, a future
plugin proposal could accidentally turn capability onboarding into a compiler
code-execution surface.

## Decision

Add Backend Plugin Sandbox Model v0 with:

- report model `src/tuc/backends/sandbox_model.py`;
- schema `schemas/backend_plugin_sandbox_model_report.v0.schema.json`;
- example `examples/backend_plugin_sandbox_model.py`;
- golden `tests/golden/backend_plugin_sandbox_model/current_report.json`;
- tests `tests/test_backend_plugin_sandbox_model.py`;
- sandbox contract `backend_plugin_sandbox_model.data_only.v0`.

The model records a required future isolation strategy:

```text
separate_worker_process_or_container_required
```

It also records that execution remains not granted:

```text
execution_permission = not_granted
execution_allowed = false
```

The model requires explicit controls for opt-in enablement, manifest pre-review,
artifact digest binding, compile-time execution denial, host-path denial,
environment-secret denial, network denial, default device denial, default
dynamic-library denial, resource budgets, content-addressed cache scoping, and
metadata-only diagnostics.

## Lifecycle Binding

Backend Plugin Lifecycle Policy now treats `sandbox_model` as satisfied by the
accepted sandbox model contract.

The lifecycle policy remains blocking because artifact provenance,
resource-budget evidence, fuzzing or negative-test evidence, and maintainer
approval are still missing.

## Security Boundary

The sandbox model is data-only. It does not implement sandboxing, discover
plugins, import modules, load dynamic libraries, execute generated artifacts,
access devices, spawn subprocesses, touch the network, inspect environment
variables, read host paths, or load benchmark artifacts.

It records stable identifiers only. It does not record Python module names,
entry points, command lines, device identifiers, source code, generated
artifacts, native library paths, secrets, or raw benchmark output.

## Consequences

TUC now has a concrete sandbox model requirement that future executable backend
plugin proposals must satisfy before implementation work can begin.

This strengthens the Universal Compute research boundary: backend capability
data can continue to flow through TUC while executable backend behavior stays
behind explicit, reviewable, least-privilege controls.
