# Backend Capability Registry

The backend capability registry is TUC's Phase 2 bridge between declarative
backend manifests and compiler/runtime planning.

It is deliberately not backend auto-discovery.

## Purpose

`BackendRegistry` collects trusted in-memory `BackendCapability` objects or
capabilities loaded from an explicit list of schema-versioned JSON manifests.
It then exposes only pure capability data to partitioning, HS-IR assignment,
diagnostics, and future backend author tooling.

The registry answers:

- Which backend names are available?
- Which capability data belongs to each name?
- Which backends claim support for an operation family?
- Which backends accept a concrete operation through pure data checks?
- Why a backend accepts or rejects a concrete operation.

It does not answer:

- Where executable plugin code lives.
- Which Python module to import.
- Which dynamic library to load.
- Which device handle to open.
- Which generated artifact to execute.

Those surfaces require separate threat models and sandboxing before they can
become part of TUC.

Capability-field assumptions, including error budgets, latency, energy,
calibration, and noise modeling, are documented in
[Backend Capability Schema](BACKEND_CAPABILITY_SCHEMA.md).

## API

```python
from tuc.backends.registry import BackendRegistry

registry = BackendRegistry.from_manifest_paths(
    [
        "examples/manifests/linear_sim_backend.json",
    ]
)

capabilities = registry.capabilities()
```

The returned `capabilities` tuple can be passed to the existing compiler or
runtime planning path:

```python
from tuc.compiler import compile_graph

result = compile_graph(graph, registry.capabilities())
```

Trusted prototype code can also construct a registry from already-created
capability objects:

```python
registry = BackendRegistry.from_capabilities([backend.capability])
```

This still registers only the `BackendCapability`; it does not store or invoke
the backend object.

## Support Diagnostics

Backend authors and compiler reviewers can ask the registry to explain support
decisions before partitioning:

```python
for diagnostic in registry.diagnose_operation_support(operation):
    print(diagnostic.backend_name, diagnostic.supported, diagnostic.reason)
```

Current reason codes include:

- `accepted`
- `unsupported_operation_kind`
- `unsupported_layout`
- `invalid_layout_attribute`
- `invalid_error_budget_attribute`
- `error_budget_exceeds_backend_limit`

Diagnostics are intentionally compact. They include backend name, operation
name, operation kind, support status, reason code, and a short detail string.
They do not include host paths, imported module names, device identifiers, or
backend execution output.

## Validation

The registry enforces:

- A maximum registered-backend count.
- Stable unique backend names.
- Backend names with an alphanumeric prefix and bounded byte length.
- Source labels that do not contain path separators.
- Immutable registration views.

Manifest loading remains handled by `tuc.manifests`, which already enforces
schema versioning, file-size budgets, duplicate-key rejection, UTF-8 decoding,
JSON value budgets, and unknown-field rejection.

## Security Model

The registry keeps backend onboarding capability-first:

- Manifest paths must be provided explicitly by the caller.
- Directories are not scanned.
- Symlinks are rejected by the manifest loader.
- Manifest fields cannot contain plugin modules, import paths, commands,
  device paths, or dynamic-library names.
- Registry diagnostics use short source labels rather than full host paths.
- Capability filtering and support diagnostics inspect only capability fields
  and already-validated operation data. They do not call backend `lower`,
  import modules, spawn processes, access devices, or execute artifacts.

This allows TUC to grow toward backend extensibility without opening a compiler
attack surface around plugin discovery.

## Current Limitations

The registry is intentionally narrow. It does not provide:

- Entry-point discovery.
- Backend package installation.
- Backend object lifecycle management.
- Native plugin ABI.
- Device discovery.
- Artifact execution.
- Sandboxing.

Those are future phases and must be introduced through explicit RFCs, security
tests, and least-privilege runtime controls.
