# Real Triton Integration Threat Model

Real Triton Integration is the first point where TUC could move from reviewed
plain data toward real ecosystem surfaces. That makes it a security boundary,
not a routine parser milestone.

The current threat model is data-only. It documents the surfaces that must stay
closed until dedicated gates exist. It does not import packages, discover
plugins, execute source, call Triton JIT, access devices, load dynamic
libraries, run subprocesses, open networks, or execute generated artifacts.

## Assets

- Developer machines and CI runners.
- Repository secrets and release credentials.
- Compiler process memory and frontend caches.
- Source Intent, metadata, HAC-IR, HS-IR, runtime plans, and evidence reports.
- Trusted prototype backend registry.
- Future device and native backend execution boundaries.

## Attacker-Controlled Inputs

- Triton or Python source buffers.
- Python packages claiming to be frontend providers.
- Plugin manifests and entrypoint declarations.
- Generated artifacts, backend artifacts, and cache metadata.
- Shape values, dtype names, tensor metadata, and fixture payloads.
- Environment-dependent package import behavior.

## Blocked Surfaces

The current gate keeps these real integration surfaces blocked:

- direct source ingestion;
- frontend package import and Python import;
- Python function object inspection;
- plugin discovery;
- Triton JIT execution;
- device access;
- dynamic library loading;
- generated artifact execution;
- native backend execution;
- subprocess execution;
- network access.

## Required Future Gates

Each surface needs a dedicated gate before it can change from blocked to
admitted:

- [Source Ingestion Quarantine Gate](SOURCE_INGESTION_QUARANTINE_GATE.md).
- [Package Import Sandbox Gate](PACKAGE_IMPORT_SANDBOX_GATE.md).
- [Plugin Discovery Allowlist Gate](PLUGIN_DISCOVERY_ALLOWLIST_GATE.md).
- [Triton JIT Execution Sandbox Gate](TRITON_JIT_EXECUTION_SANDBOX_GATE.md).
- [Device Access Sandbox Gate](DEVICE_ACCESS_SANDBOX_GATE.md).
- Generated Artifact Quarantine Gate.
- Native Backend Execution Security Gate.

Those gates must define resource budgets, isolation, allowed inputs, forbidden
outputs, diagnostics, artifact provenance, negative tests, and failure behavior
before any implementation path can execute external code or touch devices.

## Current Boundary

[Triton Integration Readiness](TRITON_INTEGRATION_READINESS.md) can be `ready`
as data-only evidence, and
[External Frontend Package Conformance](EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE.md)
can prove package-shaped plain-data fixtures without imports.

That still does not grant execution permission. The current admission gate is
therefore intentionally blocked until every real execution surface has its own
reviewed threat model and gate.

## Current Surface-Gate Evidence

The first dedicated surface gate is
[Source Ingestion Quarantine Gate](SOURCE_INGESTION_QUARANTINE_GATE.md). Its
canonical doc path is `docs/SOURCE_INGESTION_QUARANTINE_GATE.md`, its entry
point is `examples/source_ingestion_quarantine_gate.py`, and its schema is
`schemas/source_ingestion_quarantine_gate_report.v0.schema.json`.

This gate establishes quarantine controls for `direct_source_ingestion`, but it
still does not admit direct source ingestion into compiler artifacts.
The second dedicated surface gate is
[Package Import Sandbox Gate](PACKAGE_IMPORT_SANDBOX_GATE.md). Its canonical
doc path is `docs/PACKAGE_IMPORT_SANDBOX_GATE.md`, its entry point is
`examples/package_import_sandbox_gate.py`, and its schema is
`schemas/package_import_sandbox_gate_report.v0.schema.json`.

This gate establishes sandbox requirements for `frontend_package_import`, but
it still does not import packages or admit Python import into TUC.

The third dedicated surface gate is
[Plugin Discovery Allowlist Gate](PLUGIN_DISCOVERY_ALLOWLIST_GATE.md). Its
canonical doc path is `docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md`, its entry
point is `examples/plugin_discovery_allowlist_gate.py`, and its schema is
`schemas/plugin_discovery_allowlist_gate_report.v0.schema.json`.

This gate establishes allowlist requirements for `plugin_discovery`, but it
still does not discover plugins, load entrypoints, scan registries, scan
filesystems, import packages, execute plugin code, or derive capability claims
from plugin code.

The fourth dedicated surface gate is
[Triton JIT Execution Sandbox Gate](TRITON_JIT_EXECUTION_SANDBOX_GATE.md). Its
canonical doc path is `docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md`, its entry
point is `examples/triton_jit_execution_sandbox_gate.py`, and its schema is
`schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json`.

This gate establishes sandbox requirements for `triton_jit_execution`, but it
still does not invoke Triton JIT, launch kernels, execute generated artifacts,
access devices, touch kernel caches, emit backend binaries, or execute source
buffers.

The fifth dedicated surface gate is
[Device Access Sandbox Gate](DEVICE_ACCESS_SANDBOX_GATE.md). Its canonical doc
path is `docs/DEVICE_ACCESS_SANDBOX_GATE.md`, its entry point is
`examples/device_access_sandbox_gate.py`, and its schema is
`schemas/device_access_sandbox_gate_report.v0.schema.json`.

This gate establishes sandbox requirements for `device_access`, but it still
does not discover devices, enumerate devices, call driver APIs, emit device
handles, allocate device memory, map device memory, perform direct memory
access, launch kernels, or serialize hardware fingerprints.