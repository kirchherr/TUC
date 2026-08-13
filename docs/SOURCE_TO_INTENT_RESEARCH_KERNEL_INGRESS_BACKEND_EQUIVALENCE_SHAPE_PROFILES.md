# Source-To-Intent Research Kernel Ingress Backend Equivalence Shape Profiles

Source-To-Intent Research Kernel Ingress Backend Equivalence Shape Profiles v0
records metadata-only portability evidence for accepted Kernel Ingress research
cases across bounded tensor shape profiles.

It extends the backend-equivalence slice from one fixture shape per case to two
declared shape profiles:

- `base`
- `alternate`

It does not add syntax, approve general Triton source ingestion, execute
`@triton.jit`, expose tensor values, or make native performance claims.

## Contract

- Shape-profile contract:
  `source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.portability.v0`
- Base backend-equivalence contract:
  `source_to_intent_research_kernel_ingress_backend_equivalence.portability.v0`
- Standard runtime equivalence contract:
  `runtime_backend_equivalence.data_only.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`
- Kernel Ingress Proof Bundle binding:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Kernel Ingress Evidence Gate binding:
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- Capability Claim binding:
  `examples/source_to_intent_research_capability_claim.py`
- Workload Scope binding:
  `examples/source_to_intent_research_kernel_ingress_workload_scope.py`
- CI entry: `.github/workflows/ci.yml`

## What It Records

For each accepted Kernel Ingress case and each shape profile, the report
records only:

- case ID, profile ID, graph name, kernel name, operation families, and
  terminal output names;
- declared tensor shapes and a digest over those shapes;
- baseline backend sequence, always `reference-cpu`;
- candidate backend sequence selected from trusted simulator capabilities;
- run IDs, trace-step counts, comparison counts, and pass status;
- reference-correctness digests for both baseline and candidate runs;
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

This artifact strengthens the Universal Compute research claim by checking
whether the same accepted Kernel Ingress Source Intent survives small,
explicit problem-size changes without changing frontend intent:

```text
Kernel Ingress Source Intent
    -> profile base
    -> profile alternate
    -> reference-cpu baseline execution
    -> capability-selected simulator execution
    -> reference correctness digests
    -> RuntimeBackendEquivalenceReport
    -> Kernel Ingress Proof Bundle
    -> Kernel Ingress Evidence Gate
    -> Capability Claim
```

The claim remains bounded. This is shape-profile portability evidence for the
current trusted research simulator scope, not a native performance claim, not
a production Triton compatibility claim, and not proof for arbitrary tensor
rank or dynamic-shape programs.

The Kernel Ingress Workload Scope binding can consume this report as source
evidence for diagnostic `workload_scope_report.v0` data. That still does not
turn the shape profiles into performance evidence.
