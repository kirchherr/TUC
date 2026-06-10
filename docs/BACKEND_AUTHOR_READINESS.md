# Backend Author Readiness

Backend Author Readiness v0 is the single deterministic summary report for the
external backend author path.

It composes the evidence that maintainers need before treating a prototype
backend as acceptable planning evidence:

1. Manifest Claim Review passed.
2. Manifest registry loaded the backend capability.
3. Compiler planning assigned the expected operation to the backend.
4. Backend conformance passed.
5. Trusted lowering handled only the assigned HAC-IR subgraph.

## Contract

- Report schema: `schemas/backend_author_readiness_report.v0.schema.json`
- Report schema version: `tuc.backend_author_readiness_report.v0`
- Contract: `backend_author_readiness.data_only.v0`
- Example: `examples/backend_author_readiness.py`
- Golden:
  `tests/golden/backend_author_readiness/external_vector_readiness_report.json`
- Tests: `tests/test_backend_author_readiness.py`

## Security Boundary

The readiness report is a summary of already bounded evidence. It does not load
manifests by itself, scan directories, import backend modules, discover
plugins, instantiate backend objects, spawn subprocesses, access devices, touch
the network, load dynamic libraries, execute generated artifacts, run JIT code,
or authorize runtime execution.

Report fields are bounded identifiers, statuses, and issue codes. The report
does not contain raw exceptions, host paths, source text, command lines,
environment variables, device identifiers, benchmark output, generated code, or
backend artifact contents.

## Required Checks

The report order is fixed:

```text
manifest_claim_review
manifest_registry
compiler_assignment
backend_conformance
assigned_subgraph_lowering
```

Any failed check derives a deterministic issue code. Report authors cannot
hand-write issue lists.

## Usage

Run the current toy backend author readiness report:

```bash
python examples/backend_author_readiness.py
```

Run the full external author path, including the readiness report and the
underlying evidence artifacts:

```bash
python examples/external_backend_author_path.py
```

Readiness means the v0 authoring evidence is internally consistent. It is not a
hardware certification, performance claim, plugin approval, or runtime
execution permission.
