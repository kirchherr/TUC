# Runtime Execution Evidence Bundle

Runtime Execution Evidence Bundle v0 is a deterministic, data-only review
bundle for one trusted runtime execution.

It answers one narrow question:

```text
Do the runtime evidence reports and execution receipt form one coherent,
metadata-only evidence set for the same graph execution?
```

## Contract

- Report schema: `schemas/runtime_execution_evidence_bundle_report.v0.schema.json`
- Report schema version: `tuc.runtime_execution_evidence_bundle_report.v0`
- Bundle contract: `runtime_execution_evidence_bundle.data_only.v0`
- Linkage policy: `embedded_metadata_reports`
- Raw value policy: `omitted_by_policy`
- Artifact status: `review_evidence`

## Embedded Reports

The bundle embeds:

- Runtime Tensor Store Evidence
- Runtime Input Manifest
- Runtime Output Manifest
- Runtime Reference Correctness
- Runtime Execution Receipt

The bundle rechecks that every embedded report has the same graph name and
passing status. It also verifies that receipt links match the embedded evidence
reports by graph name, evidence contract, metadata digest, item count, pass
status, and raw-value policy.

## Evidence

Run:

```bash
python examples/runtime_execution_evidence_bundle.py
```

Golden evidence:

```text
tests/golden/runtime_execution_evidence_bundle/proof_of_execution.json
```

## Security Boundary

The bundle does not serialize tensor values, reference values, source text,
Python modules, commands, file paths, host paths, backend artifacts, generated
code, raw benchmark output, device identifiers, URLs, environment variables, or
plugin entry points.

It does not discover plugins, access devices, spawn subprocesses, run JIT code,
load dynamic libraries, touch the network, execute generated artifacts, or load
artifact files from matrix identifiers.

## Review Meaning

A passing Runtime Execution Evidence Bundle proves that one execution's
metadata-only evidence reports and receipt are mutually coherent and bound to
the same graph execution.

It is not a native performance claim, a cryptographic attestation, a hardware
endorsement, or a tensor-content hash.
