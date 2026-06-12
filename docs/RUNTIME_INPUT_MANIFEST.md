# Runtime Input Manifest

Runtime Input Manifest v0 is a deterministic, data-only review artifact for the
external graph inputs accepted by Runtime Executor v0.

It answers one narrow question:

```text
Which external inputs did the trusted runtime accept for this graph, and under
which metadata-only contract?
```

## Contract

- Report schema: `schemas/runtime_input_manifest_report.v0.schema.json`
- Report schema version: `tuc.runtime_input_manifest_report.v0`
- Manifest contract: `runtime_input_manifest.data_only.v0`
- Runtime input contract: `runtime_executor.numpy_float64_inputs.v0`
- External input policy: `graph_external_inputs`
- Raw value policy: `omitted_by_policy`
- Artifact status: `review_evidence`

## Evidence

Run:

```bash
python examples/runtime_input_manifest.py
```

Golden evidence:

```text
tests/golden/runtime_input_manifest/proof_of_execution.json
```

The manifest records:

- graph name
- expected external input tensors
- observed runtime input records
- shape and dtype metadata
- value role, producer kind, and producer id
- read-only runtime value status
- raw value omission policy
- blocked execution surfaces inherited from Runtime Executor v0
- a digest over input metadata only

## Security Boundary

The manifest never serializes tensor values. It does not include source text,
Python modules, commands, file paths, host paths, backend artifacts, generated
code, raw benchmark output, device identifiers, URLs, environment variables, or
plugin entry points.

The manifest does not discover plugins, access devices, spawn subprocesses, run
JIT code, load dynamic libraries, touch the network, or execute generated
artifacts. It only inspects already-created `RuntimeValueRecord` metadata from
the trusted in-process executor.

## Review Meaning

A passing Runtime Input Manifest proves that all graph external inputs expected
by HAC-IR were present as read-only runtime value records with the expected
shape, dtype, role, and provenance metadata.

It is not a parser, a source-language contract, a user input validation layer,
or a performance claim.
