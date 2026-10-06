# RFC 0337: Bounded Model Artifact Bundle

- Status: Implemented candidate
- Date: 2026-10-06

## Context

RFC 0336 returns a validated in-memory object containing a fixed-parameter
model identity, capability-planned bindings, decision evidence and inert C11 or
CUDA source artifacts. A caller that needs to transfer this result lacks one
portable representation with a closed integrity and resource contract.

## Decision

TUC adds contract `tuc.bounded_model_artifact_bundle.v0` as canonical ASCII
JSON terminated by one newline. The envelope contains:

- model, model-compilation, Source Intent and backend-binding digests;
- exact FP32 parameter bits and explicit variable-input/output tensor bindings;
- the deterministic compiler decision report;
- exactly `generated.c`, `generated.h`, `kernels.cuh`, `manifest.json` and
  `schedule.h`, each as inert text with its SHA-256 digest; and
- an envelope digest over the canonical payload.

Creation first compiles and deeply validates the RFC 0336 result. Inspection
accepts untrusted bytes but requires the closed schema, canonical encoding,
exact file set, bounded names/shapes/counts/sizes and matching hashes. Full
validation recomputes the complete envelope from the original model and
backend capabilities and requires constant-time byte equality.

## Security boundary

The envelope is data, not authority. Creation, inspection and validation do
not read or write files, contact a network, discover or load plugins, launch a
subprocess, access a device, call a native compiler or execute generated code.
The total envelope is capped at 4 MiB and existing bounded-DAG limits constrain
its components. All malformed inputs fail with
`model_artifact_bundle_rejected`.

Persistence, compilation, signing, distribution, loading and execution remain
separate caller-owned trust decisions.

## Acceptance

The implementation is acceptable when tests demonstrate:

1. deterministic canonical bytes independent of backend-binding input order;
2. exact preservation of FP32 parameter bits, public bindings and file text;
3. rejection of duplicate keys, non-canonical input, digest drift, oversize
   input and model/capability substitution;
4. CPU, CUDA and mixed-capability integration reports from the public API;
5. an installed-wheel consumer producing the committed closed, source-free
   report; and
6. no filesystem, runtime, plugin, device, compiler, subprocess or generated
   execution surface in the bundle module.

## Non-claims

This RFC does not provide a package manager, archive format, signature,
provenance service, native compiler, loader, runtime, deployment protocol,
performance evidence or general model-format compatibility. It does not make
generated C11 or CUDA safe to compile or execute.
