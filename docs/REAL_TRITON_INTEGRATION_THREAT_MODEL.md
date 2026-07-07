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

- Source Ingestion Quarantine Gate.
- Package Import Sandbox Gate.
- Plugin Discovery Allowlist Gate.
- Triton JIT Execution Sandbox Gate.
- Device Access Sandbox Gate.
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
