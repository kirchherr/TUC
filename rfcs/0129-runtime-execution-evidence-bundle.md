# RFC 0129: Runtime Execution Evidence Bundle

## Status

Accepted.

## Context

Runtime Execution Receipt v0 links metadata-only evidence reports by digest.
Runtime Evidence Gate verifies the same binding during CI-facing review.

For human review and downstream tooling, the reports are still split across
separate artifacts. That makes the evidence correct but less convenient to
inspect as one execution proof package.

## Decision

Add Runtime Execution Evidence Bundle v0 as a data-only review artifact.

The schema is `schemas/runtime_execution_evidence_bundle_report.v0.schema.json`.

The bundle embeds:

- Runtime Tensor Store Evidence
- Runtime Input Manifest
- Runtime Output Manifest
- Runtime Reference Correctness
- Runtime Execution Receipt

The bundle verifies:

- all embedded reports are for the same graph name
- all embedded reports pass
- the receipt links match the embedded reports by graph name, contract,
  metadata digest, item count, pass status, and raw-value policy

The bundle is a derived review artifact. It does not replace Runtime Evidence
Gate and is not required for runtime-evidence completeness in Runtime Evidence
Matrix v0.

## Security Boundary

The bundle is metadata-only. It does not serialize tensor values, reference
values, source text, Python modules, commands, host paths, backend artifacts,
generated code, raw benchmark output, device identifiers, URLs, environment
variables, or plugin entry points.

It does not discover plugins, access devices, spawn subprocesses, run JIT code,
load dynamic libraries, touch the network, execute generated artifacts, or load
artifact files from matrix identifiers.

## Consequences

Reviewers can inspect one deterministic evidence package for a proof execution
without giving the report authority to execute code or inspect raw values.

Future attestation, signing, or archive packaging work can build on the bundle
metadata digest without changing the runtime executor trust boundary.
