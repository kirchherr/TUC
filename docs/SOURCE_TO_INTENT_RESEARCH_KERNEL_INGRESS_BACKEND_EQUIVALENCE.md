# Source-To-Intent Research Kernel Ingress Backend Equivalence

Source-To-Intent Research Kernel Ingress Backend Equivalence v0 records
metadata-only portability evidence for accepted Kernel Ingress research cases.

It compares the same Kernel Ingress Source Intent against:

- a neutral `reference-cpu` baseline placement;
- a capability-selected trusted simulator placement using `linear-sim` and
  `vector-sim`.

It does not add syntax, approve general Triton source ingestion, execute
`@triton.jit`, expose tensor values, or make native performance claims.

## Contract

- Backend equivalence contract:
  `source_to_intent_research_kernel_ingress_backend_equivalence.portability.v0`
- Standard runtime equivalence contract:
  `runtime_backend_equivalence.data_only.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_backend_equivalence_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_backend_equivalence.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_backend_equivalence.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_backend_equivalence.py`
- Kernel Ingress Proof Bundle binding:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Kernel Ingress Evidence Gate binding:
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- Capability Claim binding:
  `examples/source_to_intent_research_capability_claim.py`
- CI entry: `.github/workflows/ci.yml`

## What It Records

For each accepted Kernel Ingress case, the report records only:

- case ID, graph name, kernel name, operation families, and terminal output
  names;
- baseline backend sequence, always `reference-cpu`;
- candidate backend sequence selected from trusted simulator capabilities;
- run IDs, trace-step counts, comparison counts, and pass status;
- `RuntimeBackendEquivalenceReport` comparison metadata digests;
- digest of the standard runtime backend equivalence report.

The current accepted cases are:

- `research_module_matmul_elementwise`
- `research_module_softmax_reduction`
- `research_module_matmul_reduction`
- `research_module_mvp_pipeline`

## Security Boundary

The report is metadata-only and value-free. It does not embed raw module
source, extracted kernel source, Source Intent payloads, tensor values,
generated code, backend binaries, benchmark output, host paths, command lines,
environment variables, device identifiers, or plugin material.

Both placements execute only through the trusted Runtime Executor registry.
The report does not import user modules, execute decorators, access devices,
load dynamic libraries, call subprocesses, perform network access, or discover
plugins.

## Review Meaning

This artifact strengthens the Universal Compute research claim by testing the
same accepted Kernel Ingress Source Intent through two backend-placement
families:

```text
Kernel Ingress Source Intent
    -> reference-cpu baseline execution
    -> capability-selected simulator execution
    -> RuntimeBackendEquivalenceReport
    -> Kernel Ingress Proof Bundle
    -> Kernel Ingress Evidence Gate
    -> Capability Claim
```

The claim remains bounded. This is portability evidence for the current trusted
research simulator scope, not a native performance claim and not a production
Triton compatibility claim.
