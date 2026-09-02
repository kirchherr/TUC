# TUC

TUC, short for **The Universal Compute**, is an early-stage research prototype.
It asks a concrete question: can a program describe a calculation without
naming a device, can target systems describe what they support, and can software
choose between those targets while preserving the calculation's result and
explaining every choice?

## What The Current Experiment Actually Does

Objective Delta v0.1.0 is deliberately small:

1. One JSON file describes a `2 x 2` matrix multiplication followed by an
   identity elementwise operation, which forwards each value unchanged. It does
   not name a CPU, GPU, or vendor.
2. Two other JSON files describe target capabilities. One accepts matrix
   multiplication and produces a blocked memory layout. The other accepts the
   elementwise operation in row-major layout.
3. TUC assigns each operation to an eligible target and records the required
   `blocked -> row_major` layout conversion.
4. Two built-in NumPy-based simulators execute the plan on the same host CPU.
5. TUC compares the result with a simple CPU reference and emits a deterministic
   metadata-only receipt describing what happened.

This proves one limited software result: for this fixed example, the compute
description can remain unchanged while data-described capabilities determine
an inspectable plan whose result matches the reference.

It does **not** prove real-hardware portability, native accelerator execution,
performance parity, arbitrary program support, or replacement of CUDA, ROCm,
XLA, TVM, IREE, Triton, or vendor compilers.

Running the experiment in several ordinary cloud VMs should reproduce it. That
is useful evidence that the released experiment is portable and deterministic
across independent environments. Because the current backends are simulators,
it is not evidence that the same code runs efficiently on different physical
accelerators. Native backends and real-device evidence remain future research.

New to compiler terminology? Start with the
[plain-language glossary](docs/GLOSSARY.md).

## Before Running The Reproduction

Treat TUC like any other unfamiliar Python package. The reproduction ZIP
contains only five bounded JSON files, but the TUC wheel is executable Python
code and NumPy is a runtime dependency. Checksums and GitHub attestations verify
artifact identity and origin; they do not prove that software is harmless.

Use a disposable VM or independently controlled CI runner, inspect the source
or pure-Python wheel when appropriate, verify the published checksums and
attestations, and disable outbound network access after obtaining the required
artifacts. The reproduction command itself requires no network, external
backend or plugin code, device, or subprocess execution. It does execute the
installed TUC and NumPy packages; a NumPy distribution may include native
components.

For a smaller review surface, the
[Objective Delta Reduced-Dependency Audit Path](docs/OBJECTIVE_DELTA_AUDIT_PATH.md)
reimplements the fixed placement, layout conversion, and `2 x 2` semantics in
one isolated standard-library script without importing TUC or NumPy. It remains
same-project code and therefore is not independent organizational evidence.

- Strategic north star: [TUC Master Plan](TUC_MASTER_PLAN.md)
- Operational status: [Roadmap Status](docs/ROADMAP_STATUS.md)
- Terminology: [Plain-language glossary](docs/GLOSSARY.md)
- Reduced-dependency Objective Delta audit:
  [Audit path](docs/OBJECTIVE_DELTA_AUDIT_PATH.md)
- First research proof path:
  [Research Onboarding Slice](docs/RESEARCH_ONBOARDING_SLICE.md)
- External feedback triage:
  [2026-06-22 Review Response](docs/EXTERNAL_REVIEW_TRIAGE_2026_06_22.md)

## Core Claims

Current narrow claim:

> Compute intent can be represented independently of hardware, planned across
> backend capabilities, executed by trusted prototype backends, and checked
> against deterministic reference semantics without changing mathematical
> intent.

TUC protects three boundaries:

- **HAC-IR:** hardware-neutral compute intent.
- **Capabilities:** backend self-description as bounded data.
- **Runtime planning:** explainable placement, movement, memory, and execution
  evidence.

Current high-level research claim artifacts:

```bash
python examples/objective_alpha_research_claim.py
python examples/objective_alpha_research_claim_gate.py
python examples/objective_beta_research_claim.py
python examples/objective_beta_research_claim_gate.py
python examples/objective_beta_reproducibility_capsule.py
python examples/objective_beta_reproducibility_gate.py
python examples/source_to_intent_research_capability_claim.py
python examples/source_to_intent_research_capability_claim_gate.py
python examples/research_scope_claim_gate.py
python examples/real_triton_first_slice_evidence_portfolio.py
python examples/objective_alpha_catalog_acyclicity_gate.py
python examples/oci_source_worker_release_provenance_readiness.py
```

The Objective Alpha claim snapshot binds the public proof bundle, catalog,
admission gates, and Source Intent mixed-runtime proof into one digest-only
review artifact. See [Objective Alpha Research Claim](docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM.md).
Schema: `schemas/objective_alpha_research_claim_report.v0.schema.json`.
Golden: `tests/golden/proofs/objective_alpha_research_claim.json`.
Gate: [Objective Alpha Research Claim Gate](docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE.md).

The [Objective Beta Research Claim](docs/OBJECTIVE_BETA_RESEARCH_CLAIM.md)
is the successor snapshot: it keeps Objective Alpha bound while adding Kernel
Ingress, First Real Triton Kernel Path, first-slice readiness, the maintainer
approval request, Research Scope Gate, kernel-isolated OCI ingestion, and OCI
worker release-provenance readiness into one digest-only research milestone. Gate:
[Objective Beta Research Claim Gate](docs/OBJECTIVE_BETA_RESEARCH_CLAIM_GATE.md).

The [Objective Beta Reproducibility Capsule](docs/OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE.md)
and [Reproducibility Gate](docs/OBJECTIVE_BETA_REPRODUCIBILITY_GATE.md)
raise that milestone to an offline-reviewable evidence closure: eleven fixed
repository artifacts, including the Beta claim and gate, are replay-verified by
digest without source, compiler, runtime, backend, plugin, device, subprocess,
network, or generated-artifact execution. Schema:
`schemas/objective_beta_reproducibility_capsule_report.v0.schema.json` and
`schemas/objective_beta_reproducibility_gate_report.v0.schema.json`. Goldens:
`tests/golden/proofs/objective_beta_reproducibility_capsule.json` and
`tests/golden/proofs/objective_beta_reproducibility_gate.json`. Start with
[Reproducing Objective Beta](docs/REPRODUCING_OBJECTIVE_BETA.md). RFC:
`rfcs/0281-objective-beta-reproducibility-capsule.md`.

The project-level
[Research Scope Claim Gate](docs/RESEARCH_SCOPE_CLAIM_GATE.md) binds the
current high-level proof gates and missing source-ingestion approval artifact by
digest, keeping production compiler, vendor replacement, native performance,
source-ingestion, plugin-execution, and generated-artifact claims explicitly
blocked.

The
[Real Triton First Slice Evidence Portfolio](docs/REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO.md)
binds the first Real Triton slice plan, maintainer review packet, missing
approval artifact, fail-closed admission gate, pre-claim acyclicity, and First
Real Triton Kernel Path into one digest-only, catalog-safe milestone while
keeping direct source ingestion blocked. Schema:
`schemas/real_triton_first_slice_evidence_portfolio_report.v0.schema.json`.
Golden:
`tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json`.
RFC: `rfcs/0274-real-triton-first-slice-evidence-portfolio.md`.

The
[Objective Alpha Catalog Acyclicity Gate](docs/OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE.md)
scans fixed catalog-entry evidence artifacts and proves they do not bind
downstream catalog or claim gates. Schema:
`schemas/objective_alpha_catalog_acyclicity_gate_report.v0.schema.json`.
Golden: `tests/golden/proofs/objective_alpha_catalog_acyclicity_gate.json`.
RFC: `rfcs/0276-objective-alpha-catalog-acyclicity-gate.md`.

Current practical Source Intent to mixed-runtime proof:

```bash
python examples/source_intent_mixed_runtime_public_proof_bundle.py
```

See
[Source Intent Mixed Runtime Public Proof Bundle](docs/SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE.md).
Schema: `schemas/source_intent_mixed_runtime_public_proof_bundle_report.v0.schema.json`.
Golden: `tests/golden/frontend/source_intent_mixed_runtime_public_proof_bundle.json`.

The stronger vertical proof now continues the same neutral Source Intent through
the exact external two-package portfolio, with no fallback and with explicit
layout conversion, trusted execution, public-output closure, independent
reference correctness, and backend equivalence:

```bash
python examples/source_intent_backend_package_portfolio.py
```

See [Source Intent Backend Package Portfolio](docs/SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO.md).
Schema: `schemas/source_intent_backend_package_portfolio_report.v0.schema.json`.
Golden: `tests/golden/frontend/source_intent_backend_package_portfolio_report.json`.
RFC: `rfcs/0285-source-intent-backend-package-portfolio.md`.

The next research slice now starts from realistic bounded Triton-like module
text and reaches the same external package portfolio without importing or
executing the module:

```bash
python examples/triton_research_backend_package_portfolio.py
```

See [Triton Research Backend Package Portfolio](docs/TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO.md).
Schema: `schemas/triton_research_backend_package_portfolio_report.v0.schema.json`.
Golden: `tests/golden/frontend/triton_research_backend_package_portfolio_report.json`.
RFC: `rfcs/0286-triton-research-backend-package-portfolio.md`.
Its exact `tl.where(x > 0, x, 0)` slice now preserves ReLU value semantics
through Source Intent, Metadata, HAC-IR, trusted execution, and independent
reference evidence; see
[Source Intent Elementwise Semantics](docs/SOURCE_INTENT_ELEMENTWISE_SEMANTICS.md)
and `rfcs/0287-source-intent-elementwise-semantics.md`.

The same vertical slice now runs its bounded parser in a fixed, resource-limited
Linux worker before parent-side Source Intent revalidation and the no-fallback
package proof. It remains explicitly non-admitting and does not claim filesystem
namespace or kernel network isolation. Run
`python examples/isolated_source_ingestion_research_proof.py`; see
[Isolated Source Ingestion Research Worker](docs/ISOLATED_SOURCE_INGESTION_RESEARCH_WORKER.md),
schema `schemas/isolated_source_ingestion_research_proof_report.v0.schema.json`,
golden `tests/golden/frontend/isolated_source_ingestion_research_proof_report.json`,
and RFC `rfcs/0288-isolated-source-ingestion-research-worker.md`.

The protected release workflow now also builds that worker as a verified
`linux/amd64` OCI Image Layout archive, emits a worker-specific CycloneDX SBOM,
requests GitHub OIDC provenance and SBOM attestations, and policy-verifies the
provenance attestation in the same GitHub-hosted run. A bounded receipt binds
the archive digest to the signer workflow, commit, ref, OIDC issuer, and run.
Run
`python examples/oci_source_worker_release_provenance_readiness.py`; see
[OCI Source Worker Release Provenance](docs/OCI_SOURCE_WORKER_RELEASE_PROVENANCE.md),
schema
`schemas/oci_source_worker_release_provenance_readiness_report.v0.schema.json`,
golden
`tests/golden/frontend/oci_source_worker_release_provenance_readiness_report.json`,
and RFC `rfcs/0290-oci-source-worker-release-provenance.md`. An executed run,
external consumer verification, public registry publication, and production
source ingestion remain blocked in repository evidence.

The hardened successor now runs that parser in a dedicated OCI container with
no network, no repository mount, read-only root filesystem, zero capabilities,
`no-new-privileges`, seccomp, and cgroup limits. It verifies those kernel facts
inside the worker and binds the resulting Source Intent digest to the existing
no-fallback backend proof. Run
`python examples/oci_source_ingestion_research_proof.py`; see
[OCI Source Ingestion Research Worker](docs/OCI_SOURCE_INGESTION_RESEARCH_WORKER.md),
schema `schemas/oci_source_ingestion_research_proof_report.v0.schema.json`,
golden `tests/golden/frontend/oci_source_ingestion_research_proof_report.json`,
and RFC `rfcs/0289-oci-source-ingestion-research-worker.md`.

## Current Proofs

Objective Alpha is the current proof shape:

```text
Graph -> HAC-IR -> Runtime Plan -> Backend A + Backend B -> Correct Result
```

Objective Delta now reproduces one bounded version of that complete semantic
path through a built wheel, an external consumer, two data-only backend
packages, and the installed public API and CLI. See
[Objective Delta Installed Portable Compute](docs/OBJECTIVE_DELTA_INSTALLED_PORTABLE_COMPUTE.md).
Its [Objective Delta Reproduction Kit](docs/OBJECTIVE_DELTA_REPRODUCTION_KIT.md)
packages the same experiment as a deterministic, attestable, data-only release
artifact with an installed replay command. Independent third-party
reproduction remains pending.

**Independent reproducer wanted:** the fixed v0.1.0 experiment takes about
20-30 minutes on CPU and requires no repository checkout. See
[GitHub issue #85](https://github.com/kirchherr/TUC/issues/85) for the exact
procedure and [Independent Reproduction Outreach](docs/INDEPENDENT_REPRODUCTION_OUTREACH.md)
for the public research invitation and review policy.

Run the proof family:

```bash
python examples/proof_of_abstraction.py
python examples/proof_of_reduction.py
python examples/proof_of_softmax.py
python examples/proof_of_execution.py
python examples/proof_of_systolic_execution.py
```

Review the proof inventory:

```bash
python examples/runtime_evidence_matrix.py
python examples/runtime_evidence_gate.py
```

Review the first-run onboarding evidence:

```bash
python examples/research_onboarding_evidence.py
```

See [Research Onboarding Evidence](docs/RESEARCH_ONBOARDING_EVIDENCE.md).

Review the Objective Alpha public proof bundle:

```bash
python examples/objective_alpha_public_proof_bundle.py
```

See [Objective Alpha Public Proof Bundle](docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE.md).
It directly exposes Proof Of Backend Equivalence plus output-closure,
transfer-boundary trace index/replay/binding, layout-transition trace
index/replay/binding, allocation-reconciliation, Source-To-Intent Research
Proof Bundle, and Kernel Ingress Evidence Gate evidence as digest-only public
entries, with an
[Objective Alpha Public Proof Bundle Gate](docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md)
to keep the top-level review surface fixed and claim-safe. The follow-on
[Objective Alpha Evidence Extension Policy](docs/OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md)
keeps future evidence growth out of the fixed 16-entry public bundle unless a
new RFC or successor evidence catalog deliberately opens that path. The
[Objective Alpha Public Evidence Catalog](docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md)
now provides that separate digest-only growth surface, with an
[Objective Alpha Public Evidence Catalog Admission Gate](docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md)
checking append-only, RFC-bound, digest-only admission rules. A typed catalog
entry admission pattern now derives the catalog's expected IDs, entry points,
artifact kinds, extension tiers, digest sources, and raw-output policies from
reviewed data-only specs. The catalog now also emits required extension-tier
coverage evidence for `governance`, `runtime_proof`,
`frontend_runtime_proof`, and `claim_boundary`, so reviewers can see that
Objective Alpha covers the current governance, backend-equivalence,
source-ingress, and claim-boundary proof roles. Its first non-governance
catalog entry binds the Runtime Backend Equivalence Portfolio as
`runtime_proof` evidence, its `frontend_runtime_proof` entries bind the
Source-To-Intent Kernel Ingress Proof Bundle, Source Intent Mixed Runtime
Public Proof Bundle, First Real Triton Kernel Path, and Real Triton First Slice
Evidence Portfolio; its `claim_boundary` entry binds the Source-To-Intent
Research Capability Claim Gate without expanding the fixed public bundle.

## Runtime Execution

Runtime Executor v0 runs already-compiled graphs through a fixed trusted
in-process executor registry. It is intentionally not a plugin system and does
not authorize external executable backend artifacts.

Current runtime surfaces:

- Runtime Execution Readiness before kernels run.
- Runtime Tensor Store v0 with internal read-only `RuntimeValueRecord` objects.
- Runtime Tensor Store Evidence v0 without serialized tensor values.
- Runtime Input Manifest v0 for graph external inputs without serialized tensor
  values.
- Runtime Output Manifest v0 for terminal graph outputs without serialized
  tensor values.
- Runtime Output Contract v0 for explicit public output aliases without
  serialized tensor values.
- Runtime Public Output Bundle v0 for resolving public aliases to read-only
  runtime values while keeping review evidence metadata-only.
- Source Intent Runtime Returns v0 for proving frontend public return intent
  resolves through Runtime Output Contract and Runtime Public Output Bundle.
- Source Intent Mixed Runtime Public Proof Bundle v0 binding Source Intent
  plain data through `systolic-sim + vector-sim` trusted execution, Runtime
  Public Output Bundle, Reference Correctness, and Backend Equivalence as one
  digest-only public proof.
- Runtime Reference Correctness v0 for output/reference comparison without
  serialized tensor values.
- Runtime Execution Receipt v0 linking runtime evidence reports, public output
  contracts, and public output bundles by metadata digest without serialized
  tensor values.
- Runtime Execution Evidence Bundle v0 packaging one coherent metadata-only
  execution evidence set, including the public output boundary, for review.
- Runtime Execution Output Closure v0 auditing that Receipt and Evidence Bundle
  bind the same public Output Contract and Public Output Bundle across
  proof-of-execution, multi-output, and softmax fixtures.
- Runtime Evidence Replay Verifier v0 replay-checking serialized Runtime
  Execution Evidence Bundle and Runtime Execution Output Closure reports by
  metadata digest without re-running source, JIT, plugins, devices, or backend
  artifacts.
- Runtime Backend Equivalence v0 comparing `reference-cpu` against
  `systolic-sim`, `vector-sim`, and mixed `systolic-sim` plus `vector-sim`
  placements without serialized tensor values, with all proof slices bound into
  the Runtime Evidence Gate.
- Proof Of Backend Equivalence v0 promoting the mixed `reference-cpu` versus
  `systolic-sim + vector-sim` placement comparison into one canonical
  metadata-only proof entrypoint.
- Mixed Runtime Tensor Store Evidence v0 proving the accepted
  `systolic-sim -> vector-sim` plan produces read-only Runtime Value Records
  with placement metadata and without serialized tensor values.
- Runtime Backend Equivalence Portfolio v0 aggregating the systolic, vector,
  and mixed accelerator equivalence slices into one backend-diversity evidence
  artifact inventoried by Runtime Evidence Matrix and bound by the Runtime
  Evidence Gate.
- Runtime Backend Equivalence Portfolio Policy v0 declaring the accepted
  portfolio slice membership and backend-family coverage as data-only evidence.
- Runtime HS-IR Plan Alignment v0 binding HS-IR backend/layout decisions to
  the accepted `PartitionPlan` and observed `RuntimeExecutionTrace`, now
  inventoried by Runtime Evidence Matrix and required by Runtime Evidence Gate
  for the mixed accelerator proof slice.
- Runtime Buffer Lifetime, Allocation Plan, Memory Budget, Allocation Request
  Manifest, Allocation Admission, Allocation Receipt, and Memory Planning Gate,
  now inventoried by Runtime Evidence Matrix and required by Runtime Evidence
  Gate through exact artifact IDs.
- Runtime Candidate Score Evidence, Policy, Conformance, and Scoring Gate.
- Runtime Planning Explanation v0 for accepted `PartitionPlan` backend
  sequence, fallback/no-fallback placement, candidate-score visibility, and
  movement accounting, now bound into Runtime Evidence Matrix and Runtime
  Evidence Gate for the systolic and mixed backend-equivalence slices.
- Runtime Transfer Evidence v0 for planned cross-domain runtime transfers as
  data-only review evidence with deterministic planning-cost estimates and no
  device-residency or native-performance claim.
- Runtime Transfer Trace Index v0 binds planned cross-domain transfers to
  concrete producer and consumer Runtime Execution Trace steps without
  materializing a transfer step, now required by Runtime Evidence Matrix and
  Runtime Evidence Gate for the systolic backend-equivalence proof slice.
- Runtime Transfer Trace Replay Verifier v0 replay-checking serialized Transfer
  Evidence and Transfer Trace Index reports by metadata digest without rerunning
  runtime execution or materializing transfer steps, now required by Runtime
  Evidence Matrix and Runtime Evidence Gate for the systolic proof slice.
- Runtime Backend Equivalence Transfer Binding v0 binding systolic backend
  equivalence to verified transfer trace replay by metadata digest, proving the
  same graph carries both terminal semantics and transfer-boundary evidence;
  now required by Runtime Evidence Matrix and Runtime Evidence Gate.
- Runtime Layout Conversion Trace Index v0 binds planned `blocked -> row_major`
  transition evidence to concrete producer and consumer Runtime Execution Trace
  steps without materializing a converter step, now required by Runtime Evidence
  Matrix and Runtime Evidence Gate for the mixed backend-equivalence proof slice.
- Runtime Layout Conversion Trace Replay Verifier v0 replay-checking serialized
  Layout Conversion Evidence and Trace Index reports by metadata digest without
  re-running runtime execution or materializing converter steps.
- Runtime Backend Equivalence Layout Binding v0 binding mixed backend
  equivalence to verified layout trace replay by metadata digest, proving the
  same graph carries both terminal semantics and layout-transition evidence.
- Runtime Materialized Layout Conversion v0 adds a separate opt-in trusted
  simulator path that performs one bounded `blocked -> row_major` buffer
  transformation, verifies exact logical values, and binds the result to
  passing mixed Backend Equivalence. The legacy executor and its explicitly
  non-materialized trace evidence remain unchanged.
- Runtime Materialized Transfer v0 extends that opt-in path with a real,
  alias-free `device_sram -> host_ram` simulator buffer copy after layout
  conversion, then binds plan, trace, output metadata, conversion evidence, and
  passing Backend Equivalence without claiming physical residency or measured
  transfer performance.
- Operation/value contract checks for shapes, `float64`, finite values, and
  MVP operation semantics.

CI-facing runtime evidence entry points:

```text
examples/runtime_evidence_gate.py
examples/runtime_tensor_store_evidence.py
examples/runtime_systolic_tensor_store_evidence.py
examples/runtime_mixed_tensor_store_evidence.py
examples/runtime_input_manifest.py
examples/runtime_execution_receipt.py
examples/runtime_execution_evidence_bundle.py
examples/runtime_execution_output_closure.py
examples/runtime_evidence_replay_verifier.py
examples/runtime_multi_output_execution_output_closure.py
examples/runtime_softmax_execution_output_closure.py
examples/runtime_backend_equivalence.py
examples/runtime_backend_equivalence_portfolio.py
examples/runtime_backend_equivalence_portfolio_policy.py
examples/runtime_vector_backend_equivalence.py
examples/runtime_mixed_backend_equivalence.py
examples/proof_of_backend_equivalence.py
examples/runtime_hs_ir_plan_alignment.py
examples/runtime_planning_explanation.py
examples/runtime_mixed_planning_explanation.py
examples/runtime_transfer_evidence.py
examples/runtime_transfer_trace_index.py
examples/runtime_transfer_trace_replay_verifier.py
examples/runtime_backend_equivalence_transfer_binding.py
examples/runtime_output_contract.py
examples/runtime_public_output_bundle.py
examples/source_intent_runtime_returns.py
examples/source_intent_mixed_runtime_public_proof_bundle.py
examples/runtime_reference_correctness.py
examples/runtime_candidate_scoring_gate.py
examples/runtime_allocation_request_manifest.py
examples/runtime_allocation_admission.py
examples/runtime_allocation_receipt.py
examples/runtime_allocation_reconciliation.py
examples/runtime_memory_planning_gate.py
examples/runtime_layout_conversion_trace_index.py
examples/runtime_layout_conversion_trace_replay_verifier.py
examples/runtime_backend_equivalence_layout_binding.py
examples/runtime_materialized_layout_conversion.py
examples/runtime_materialized_transfer.py
```

Key docs:

- [Runtime Executor](docs/RUNTIME_EXECUTOR.md)
- [Runtime Evidence Flow](docs/RUNTIME_EVIDENCE_FLOW.md)
- [Objective Alpha Research Claim](docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM.md)
- [Objective Alpha Research Claim Gate](docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE.md)
- [Objective Alpha Public Proof Bundle Gate](docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md)
- [Objective Alpha Evidence Extension Policy](docs/OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md)
- [Objective Alpha Public Evidence Catalog](docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md)
- [Objective Alpha Public Evidence Catalog Admission Gate](docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md)
- [Objective Alpha Catalog Acyclicity Gate](docs/OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE.md)
- [Runtime Tensor Store](docs/RUNTIME_TENSOR_STORE.md)
- [Runtime Tensor Store Evidence](docs/RUNTIME_TENSOR_STORE_EVIDENCE.md)
- [Runtime Input Manifest](docs/RUNTIME_INPUT_MANIFEST.md)
- [Runtime Output Manifest](docs/RUNTIME_OUTPUT_MANIFEST.md)
- [Runtime Execution Receipt](docs/RUNTIME_EXECUTION_RECEIPT.md)
- [Runtime Execution Evidence Bundle](docs/RUNTIME_EXECUTION_EVIDENCE_BUNDLE.md)
- [Runtime Execution Output Closure](docs/RUNTIME_EXECUTION_OUTPUT_CLOSURE.md)
- [Runtime Evidence Replay Verifier](docs/RUNTIME_EVIDENCE_REPLAY_VERIFIER.md)
- [Runtime Backend Equivalence](docs/RUNTIME_BACKEND_EQUIVALENCE.md)
- [Proof Of Backend Equivalence](docs/PROOF_OF_BACKEND_EQUIVALENCE.md)
- [Runtime Backend Equivalence Portfolio](docs/RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO.md)
- [Runtime Evidence Gate Matrix Coverage](docs/RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE.md)
- [Runtime HS-IR Plan Alignment](docs/RUNTIME_HS_IR_PLAN_ALIGNMENT.md)
- [Runtime Planning Explanation](docs/RUNTIME_PLANNING_EXPLANATION.md)
- [Runtime Transfer Evidence](docs/RUNTIME_TRANSFER_EVIDENCE.md)
- [Runtime Transfer Trace Index](docs/RUNTIME_TRANSFER_TRACE_INDEX.md)
- [Runtime Transfer Trace Replay Verifier](docs/RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER.md)
- [Runtime Backend Equivalence Transfer Binding](docs/RUNTIME_BACKEND_EQUIVALENCE_TRANSFER_BINDING.md)
- [Runtime Layout Conversion Evidence](docs/RUNTIME_LAYOUT_CONVERSION_EVIDENCE.md)
- [Runtime Layout Conversion Trace Index](docs/RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX.md)
- [Runtime Layout Conversion Trace Replay Verifier](docs/RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER.md)
- [Runtime Backend Equivalence Layout Binding](docs/RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING.md)
- [Runtime Materialized Layout Conversion](docs/RUNTIME_MATERIALIZED_LAYOUT_CONVERSION.md)
- [Runtime Materialized Transfer](docs/RUNTIME_MATERIALIZED_TRANSFER.md)
- [Runtime Output Contract](docs/RUNTIME_OUTPUT_CONTRACT.md)
- [Runtime Public Output Bundle](docs/RUNTIME_PUBLIC_OUTPUT_BUNDLE.md)
- [Source Intent Mixed Runtime Public Proof Bundle](docs/SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE.md)
- [Runtime Reference Correctness](docs/RUNTIME_REFERENCE_CORRECTNESS.md)
- [Runtime Allocation Request Manifest](docs/RUNTIME_ALLOCATION_REQUEST_MANIFEST.md)
- [Runtime Allocation Admission](docs/RUNTIME_ALLOCATION_ADMISSION.md)
- [Runtime Allocation Receipt](docs/RUNTIME_ALLOCATION_RECEIPT.md)
- [Runtime Allocation Reconciliation](docs/RUNTIME_ALLOCATION_RECONCILIATION.md)
- [Runtime Memory Planning Gate](docs/RUNTIME_MEMORY_PLANNING_GATE.md)
- [Runtime Candidate Scoring Gate](docs/RUNTIME_CANDIDATE_SCORING_GATE.md)
- [Runtime override policy](docs/RUNTIME_OVERRIDE_POLICY.md)

Runtime schemas:

```text
schemas/runtime_input_manifest_report.v0.schema.json
schemas/runtime_execution_receipt_report.v0.schema.json
schemas/runtime_execution_evidence_bundle_report.v0.schema.json
schemas/runtime_execution_output_closure_report.v0.schema.json
schemas/runtime_evidence_replay_verifier_report.v0.schema.json
schemas/runtime_backend_equivalence_report.v0.schema.json
schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json
schemas/runtime_backend_equivalence_portfolio_policy_report.v0.schema.json
schemas/runtime_evidence_gate_matrix_coverage_report.v0.schema.json
schemas/runtime_hs_ir_plan_alignment_report.v0.schema.json
schemas/runtime_planning_explanation_report.v0.schema.json
schemas/runtime_transfer_evidence_report.v0.schema.json
schemas/runtime_transfer_trace_index_report.v0.schema.json
schemas/runtime_transfer_trace_replay_verifier_report.v0.schema.json
schemas/runtime_backend_equivalence_transfer_binding_report.v0.schema.json
schemas/runtime_layout_conversion_trace_index_report.v0.schema.json
schemas/runtime_layout_conversion_trace_replay_verifier_report.v0.schema.json
schemas/runtime_backend_equivalence_layout_binding_report.v0.schema.json
schemas/runtime_output_contract_report.v0.schema.json
schemas/runtime_public_output_bundle_report.v0.schema.json
schemas/source_intent_runtime_returns_report.v0.schema.json
schemas/source_intent_mixed_runtime_public_proof_bundle_report.v0.schema.json
schemas/runtime_allocation_request_manifest_report.v0.schema.json
schemas/runtime_allocation_admission_report.v0.schema.json
schemas/runtime_allocation_receipt_report.v0.schema.json
schemas/runtime_allocation_reconciliation_report.v0.schema.json
```

## Frontend Intake

TUC does not accept Triton/Python source as a default compiler input path and
does not execute source code.

TUC's frontend goal is a research proof of a safe source-intent boundary, not a
claim that this project replaces CUDA, ROCm, XLA, TVM, or production vendor
compiler stacks.

Accepted intake path:

```text
schema-versioned metadata or Source Intent data
    -> intake report
    -> ComputeGraph
    -> HAC-IR
```

Current frontend surfaces:

- Triton-like metadata adapter.
- Execution-free Triton Source Preflight.
- Explicit Source-To-Intent Research Parser v0 for a tiny caller-provided
  Triton-like source subset that emits only validated `source_intent.v0` plain
  data.
- Source-To-Intent Research Parser Conformance Gate proving the first parser
  output slice passes the reusable Source Intent Frontend Conformance path.
- Source-To-Intent Research Diagnostics proving accepted parser cases and
  whitelisted rejected cases, including annotated signatures, remain
  deterministic, source-free, and bounded.
- Source-To-Intent Research Preflight Bridge proving accepted and rejected
  parser diagnostics, including annotation rejection, remain gated by
  execution-free Triton Source Preflight.
- Source-To-Intent Research Evidence Gate binding research readiness,
  conformance, and diagnostics by digest.
- Source-To-Intent Research Execution Bridge proving accepted parser output can
  re-enter Source Intent Intake and reach controlled Runtime Executor evidence.
- Source-To-Intent Research Idiom Alignment proving accepted parser slices stay
  within the already covered Triton-like MVP idiom scope.
- Source-To-Intent Research Proof Bundle providing one digest-only review entry
  for the current safe source-to-runtime research slice.
- Source-To-Intent Research Capability Claim summarizing the currently
  supported bounded Universal Compute research slice and explicitly blocking
  production parser, native performance, hardware certification, arbitrary
  backend execution, and vendor compiler replacement claims.
- Source-To-Intent Research Capability Claim Gate binding that high-level
  claim into CI as source-free text evidence, including the exact thirteen
  evidence IDs that support the bounded research claim.
- Source-To-Intent Research Source Runtime Smoke proving accepted source
  buffers can run end-to-end through the controlled research path.
- Source-To-Intent Research Kernel Ingress proving realistic Triton
  module-shaped source buffers with a fixed import prelude and one plain
  `@triton.jit` kernel can be validated, extracted, and executed through the
  same controlled research path, currently across
  `matmul_elementwise`, `softmax_reduction`, `matmul_reduction`,
  `softmax_elementwise`, and the combined `mvp_pipeline` slice.
- Source-To-Intent Research Kernel Ingress Runtime Matrix making accepted
  module-shaped runtime coverage explicit by backend sequence, terminal output,
  trace-step count, and runtime evidence digest.
- Source-To-Intent Research Kernel Ingress Backend Equivalence proving accepted
  module-shaped Source Intent preserves terminal public outputs under a
  neutral `reference-cpu` baseline and capability-selected trusted simulator
  placements.
- Source-To-Intent Research Kernel Ingress Runtime Coverage Policy requiring
  current accepted runtime cases, backend sequences, terminal outputs, and
  runtime digest fields before Kernel Ingress proof evidence can pass.
- Source-To-Intent Research Kernel Ingress Runtime Backend Alignment binding
  accepted backend sequences to trusted Runtime Executor conformance for
  `linear-sim` and `vector-sim`.
- Source-To-Intent Research Kernel Ingress Boundary Budget proving accepted
  module-shaped inputs stay within resource limits and budget overflow rejects
  before extraction or lowering.
- Source-To-Intent Research Kernel Ingress Rejection Coverage proving current
  diagnostics and budget rejection surfaces are source-free and complete,
  including import-preamble drift and annotated-signature rejection.
- Source-To-Intent Research Kernel Ingress Conformance Gate proving Kernel
  Ingress outputs pass the reusable Source Intent Frontend Conformance path.
- Source-To-Intent Research Kernel Ingress Diagnostics proving accepted and
  rejected module-shaped source cases, including annotated signatures, stay
  source-free, bounded, and fail-closed.
- Source-To-Intent Research Kernel Ingress Idiom Alignment proving accepted
  module-shaped source outputs remain inside covered Triton MVP idioms.
- Source-To-Intent Research Kernel Ingress Proof Bundle giving reviewers one
  digest-only entry point for the Kernel Ingress research slice.
- Source-To-Intent Research Kernel Ingress Evidence Gate binding the focused
  Kernel Ingress proof slice as CI-facing source-free evidence.
- First Real Triton Kernel Path giving reviewers one compact, digest-bound
  proof for the `mvp_pipeline` research case across Kernel Ingress, Source
  Intent re-intake, trusted runtime execution, backend-equivalence evidence,
  and fail-closed source-ingestion admission. Schema:
  `schemas/first_real_triton_kernel_path_report.v0.schema.json`; entry point:
  `examples/first_real_triton_kernel_path.py`; golden:
  `tests/golden/frontend/first_real_triton_kernel_path.json`; doc:
  `docs/FIRST_REAL_TRITON_KERNEL_PATH.md`; RFC:
  `rfcs/0272-first-real-triton-kernel-path.md`.
- Triton Integration Readiness defining the next Real Triton Integration
  milestone as data-only review evidence with direct source ingestion and JIT
  execution still blocked. Schema: `schemas/triton_integration_readiness_report.v0.schema.json`; entry point: `examples/triton_integration_readiness.py`.
- Real Triton Integration Admission Gate binding readiness, external frontend
  conformance, and threat-model evidence by digest while admission stays
  blocked because each real integration surface remains guarded by a
  non-admitting dedicated gate. Schema: `schemas/real_triton_integration_admission_gate_report.v0.schema.json`; entry point: `examples/real_triton_integration_admission_gate.py`; docs: `docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md`, `docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md`.
- Source Ingestion Quarantine Gate establishing the first dedicated Real Triton
  Integration surface gate for `direct_source_ingestion`, with source buffers
  treated as untrusted, preflight-only, digest-only evidence and no
  source-to-ComputeGraph/HAC-IR/runtime-plan path admitted. Schema: `schemas/source_ingestion_quarantine_gate_report.v0.schema.json`; entry point: `examples/source_ingestion_quarantine_gate.py`; doc: `docs/SOURCE_INGESTION_QUARANTINE_GATE.md`.
- Package Import Sandbox Gate establishing the next dedicated Real Triton
  Integration surface gate for `frontend_package_import`, with external package
  integration kept manifest/fixture-only and no Python import, package code
  execution, entrypoint discovery, network, filesystem, environment,
  subprocess, or dynamic-library surface admitted. Schema: `schemas/package_import_sandbox_gate_report.v0.schema.json`; entry point: `examples/package_import_sandbox_gate.py`; doc: `docs/PACKAGE_IMPORT_SANDBOX_GATE.md`.
- Plugin Discovery Allowlist Gate establishing the third dedicated Real Triton
  Integration surface gate for `plugin_discovery`, with plugin discovery,
  entrypoint discovery, registry scans, filesystem scans, plugin code
  execution, frontend package import, Python import, network, subprocess,
  dynamic-library, and device surfaces still blocked. Schema: `schemas/plugin_discovery_allowlist_gate_report.v0.schema.json`; entry point: `examples/plugin_discovery_allowlist_gate.py`; doc: `docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md`.
- Triton JIT Execution Sandbox Gate establishing the fourth dedicated Real
  Triton Integration surface gate for `triton_jit_execution`, with JIT,
  kernel launch, generated artifact execution, device access, kernel-cache
  access, backend binary emission, package import, Python import, plugin
  discovery, network, subprocess, and dynamic-library surfaces still blocked. Schema: `schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json`; entry point: `examples/triton_jit_execution_sandbox_gate.py`; doc: `docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md`.
- Device Access Sandbox Gate establishing the fifth dedicated Real Triton
  Integration surface gate for `device_access`, with device discovery,
  enumeration, driver calls, device handles, device memory allocation, memory
  mapping, direct memory access, kernel launch, generated artifact execution,
  subprocess, and dynamic-library surfaces still blocked. Schema: `schemas/device_access_sandbox_gate_report.v0.schema.json`; entry point: `examples/device_access_sandbox_gate.py`; doc: `docs/DEVICE_ACCESS_SANDBOX_GATE.md`.
- Generated Artifact Quarantine Gate establishing the sixth dedicated Real
  Triton Integration surface gate for `generated_artifact_execution`, with
  artifact emission, writes, loads, executable permissions, artifact-cache
  access, backend binary emission, device access, kernel launch, subprocess,
  and dynamic-library surfaces still blocked. Schema: `schemas/generated_artifact_quarantine_gate_report.v0.schema.json`; entry point: `examples/generated_artifact_quarantine_gate.py`; doc: `docs/GENERATED_ARTIFACT_QUARANTINE_GATE.md`.
- Native Backend Execution Security Gate establishing the seventh dedicated Real
  Triton Integration surface gate for `native_backend_execution`, with native
  backend execution, native plugin ABI loading, backend plugin execution,
  symbol resolution, FFI calls, unsafe memory access, dynamic-library loading,
  generated artifact execution, device access, kernel launch, and subprocess
  surfaces still blocked. Schema: `schemas/native_backend_execution_security_gate_report.v0.schema.json`; entry point: `examples/native_backend_execution_security_gate.py`; doc: `docs/NATIVE_BACKEND_EXECUTION_SECURITY_GATE.md`.
- Real Triton Surface Gate Completion binding Real Triton Admission and all
  seven dedicated surface gates by digest, proving the surface-gate set is
  complete while admission remains blocked and every surface gate remains
  non-admitting. Schema: `schemas/real_triton_surface_gate_completion_report.v0.schema.json`; entry point: `examples/real_triton_surface_gate_completion.py`; doc: `docs/REAL_TRITON_SURFACE_GATE_COMPLETION.md`.
- Real Triton First Slice Plan identifying `direct_source_ingestion` as the
  first candidate admitting slice while keeping `admitted = false` and now
  binding thirteen current evidence artifacts, including CI replay and Source Ingestion Approval Criteria, before any implementation can open that surface; only maintainer security review remains as admission evidence, and downstream review/approval gates bind this plan without creating circular evidence. Schema: `schemas/real_triton_first_slice_plan_report.v0.schema.json`; entry point: `examples/real_triton_first_slice_plan.py`; doc: `docs/REAL_TRITON_FIRST_SLICE_PLAN.md`.
- Real Triton First Slice Admission Readiness Gate binding the first-slice plan,
  maintainer review packet, missing approval artifact, admission gate, first
  real kernel path, evidence portfolio, and catalog acyclicity by digest while
  keeping `gate_passed = false`, `admission_ready = false`, and `admitted = false`
  until external maintainer approval exists. Schema: `schemas/real_triton_first_slice_admission_readiness_gate_report.v0.schema.json`; entry point: `examples/real_triton_first_slice_admission_readiness_gate.py`; golden: `tests/golden/frontend/real_triton_first_slice_admission_readiness_gate_report.json`; doc: `docs/REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE.md`; RFC: `rfcs/0277-real-triton-first-slice-admission-readiness-gate.md`.
- Real Triton First Slice Maintainer Approval Request packaging the readiness
  gate, maintainer review packet, missing approval artifact, and admission gate
  by digest for external maintainer review while recording
  `approval_request_is_approval = false`, `approval_status = not_approved`,
  `admission_ready = false`, and `admitted = false`. Schema: `schemas/real_triton_first_slice_maintainer_approval_request_report.v0.schema.json`; entry point: `examples/real_triton_first_slice_maintainer_approval_request.py`; golden: `tests/golden/frontend/real_triton_first_slice_maintainer_approval_request_report.json`; doc: `docs/REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST.md`; RFC: `rfcs/0278-real-triton-first-slice-maintainer-approval-request.md`.
- Admitting Source Ingestion RFC defining the requirements-only first
  `direct_source_ingestion` slice boundary while keeping implementation and
  admission blocked. Doc: `docs/ADMITTING_SOURCE_INGESTION_RFC.md`.
- CI Replay For Admitted Slice binding the future first source-ingestion slice to read-only GitHub Actions replay of the bounded buffer, sandbox, negative corpus, source-free diagnostics, and plain-data golden evidence. Schema: `schemas/ci_replay_for_admitted_slice_report.v0.schema.json`; entry point: `examples/ci_replay_for_admitted_slice.py`; doc: `docs/CI_REPLAY_FOR_ADMITTED_SLICE.md`.
- Source Ingestion Approval Criteria defining the objective, non-admitting checks a future maintainer approval must satisfy before `direct_source_ingestion` can open. Schema: `schemas/source_ingestion_approval_criteria_report.v0.schema.json`; entry point: `examples/source_ingestion_approval_criteria.py`; doc: `docs/SOURCE_INGESTION_APPROVAL_CRITERIA.md`.
- Source Ingestion Maintainer Security Review Packet collecting the admitted-slice RFC, buffer, sandbox, fuzz, diagnostics, golden, CI replay, approval criteria, and first-slice plan reports by digest for human security review while recording `approval_status = not_approved` and keeping source ingestion blocked. Schema: `schemas/source_ingestion_maintainer_security_review_packet_report.v0.schema.json`; entry point: `examples/source_ingestion_maintainer_security_review_packet.py`; doc: `docs/SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md`.
- Source Ingestion Maintainer Approval Artifact binding the review packet and recording `external_approval_not_supplied` while keeping `approval_artifact_present = false`. Schema: `schemas/source_ingestion_maintainer_approval_artifact_report.v0.schema.json`; entry point: `examples/source_ingestion_maintainer_approval_artifact.py`; doc: `docs/SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md`.
- Source Ingestion Admission Gate binding the maintainer-review packet and missing-approval artifact into a fail-closed decision point with `admitted = false`, `approval_artifact_present = false`, and `source_ingestion_admission_ready = false` until external maintainer approval exists. Schema: `schemas/source_ingestion_admission_gate_report.v0.schema.json`; entry point: `examples/source_ingestion_admission_gate.py`; doc: `docs/SOURCE_INGESTION_ADMISSION_GATE.md`.
- Source Ingestion Pre-Claim Acyclicity Gate proving the source-ingestion First-Slice -> Review -> Approval -> Admission digest graph is acyclic before Research Scope binds it, while explicitly excluding `research_scope_claim_gate` from the pre-claim graph. Schema: `schemas/source_ingestion_preclaim_acyclicity_gate_report.v0.schema.json`; entry point: `examples/source_ingestion_preclaim_acyclicity_gate.py`; doc: `docs/SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE.md`.
- Evidence Graph Acyclicity Gate proving the current source-ingestion First-Slice -> Review -> Approval -> Admission -> Pre-Claim Acyclicity -> Research-Scope digest graph is acyclic, source-free, and edge-digest-only. Schema: `schemas/evidence_graph_acyclicity_gate_report.v0.schema.json`; entry point: `examples/evidence_graph_acyclicity_gate.py`; doc: `docs/EVIDENCE_GRAPH_ACYCLICITY_GATE.md`.
- Bounded Source Buffer API validating source text as untrusted bounded data
  and emitting source-free metadata records without admitting source-to-IR or
  source-to-runtime paths. Doc: `docs/BOUNDED_SOURCE_BUFFER_API.md`.
- Source Ingestion Sandbox Implementation wrapping the bounded source buffer in
  an execution-free non-admitting sandbox, binding its evidence by digest while
  keeping Source Intent, graph, HAC-IR, and runtime-plan outputs blocked. Doc: `docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md`.
- Parser Fuzz Negative Corpus For Admitting Slice defining deterministic
  source-free rejection seeds for the future admitting parser path while keeping
  Source Intent, graph, HAC-IR, and runtime-plan outputs blocked. Doc: `docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md`.
- Source-Free Diagnostics Admission Tests proving public parser rejection
  diagnostics stay digest-only, reason-code based, and non-admitting. Doc: `docs/SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md`.
- Source-To-Intent Next Syntax Slice proving branched dataflow, fanout reuse,
  all MVP operation families, and multiple public returns through source-free
  semantic mapping evidence. Schema: `schemas/source_to_intent_next_syntax_report.v0.schema.json`; entry point: `examples/source_to_intent_next_syntax_slice.py`; doc: `docs/SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md`.
- External Frontend Package Conformance proving an external frontend can be
  reviewed as a data-only Source Intent package manifest plus digest-only
  fixtures without package import, plugin discovery, source ingestion, or JIT.
  Schema: `schemas/external_frontend_package_conformance_report.v0.schema.json`; entry point: `examples/external_frontend_package_conformance.py`; doc: `docs/EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE.md`.
- Source Intent IR, schema, intake, return semantics, conformance, and metadata
  conversion.
- Source Intent Axis Attributes for neutral `softmax` and `reduction` axis
  semantics.
- Source Intent Frontend Conformance Gate for CI-facing external frontend
  plain-data and public-return evidence.
- Source Intent Runtime Returns evidence connecting explicit frontend returns
  to runtime public outputs after trusted execution.
- Source-To-Intent Parser Block Gate proving the default source parser path
  remains intentionally closed.
- Source-To-Intent Corpus Evidence defining accepted and rejected source-buffer
  fixtures for the first narrow parser proof without emitting Source Intent IR.
- Source-To-Intent Property Corpus evidence defining fuzz/property obligations
  for the first narrow parser proof without running parser logic.
- Source-To-Intent Parser Report v0 defining a proposal-only parser report
  golden with `parser_enabled = false`.
- Source-To-Intent Research Readiness evidence showing current progress toward
  the first narrow parser proof while the default parser path remains closed.
- The default Source-to-Intent parser path remains blocked; the explicit
  research parser is not wired into compiler intake and does not bypass Source
  Intent Intake.

CI-facing frontend evidence entry points:

```text
examples/source_intent_frontend_conformance_gate.py
examples/source_intent_frontend_conformance.py
examples/source_intent_runtime_returns.py
examples/source_intent_mixed_runtime_public_proof_bundle.py
examples/source_to_intent_corpus.py
examples/source_to_intent_property_corpus.py
examples/source_to_intent_parser_report.py
examples/source_to_intent_research_parser.py
examples/source_to_intent_research_parser_conformance_gate.py
examples/source_to_intent_research_diagnostics.py
examples/source_to_intent_research_preflight_bridge.py
examples/source_to_intent_research_execution_bridge.py
examples/source_to_intent_research_idiom_alignment.py
examples/source_to_intent_research_evidence_gate.py
examples/source_to_intent_research_proof_bundle.py
examples/source_to_intent_research_capability_claim.py
examples/source_to_intent_research_capability_claim_gate.py
examples/source_to_intent_research_kernel_ingress.py
examples/source_to_intent_research_kernel_ingress_runtime_matrix.py
examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py
examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py
examples/source_to_intent_research_kernel_ingress_runtime_output_closure_index.py
examples/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py
examples/source_to_intent_research_kernel_ingress_backend_equivalence.py
examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py
examples/source_to_intent_research_kernel_ingress_workload_scope.py
examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py
examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py
examples/source_to_intent_research_kernel_ingress_boundary_budget.py
examples/source_to_intent_research_kernel_ingress_rejection_coverage.py
examples/source_to_intent_research_kernel_ingress_conformance_gate.py
examples/source_to_intent_research_kernel_ingress_diagnostics.py
examples/source_to_intent_research_kernel_ingress_idiom_alignment.py
examples/source_to_intent_research_kernel_ingress_proof_bundle.py
examples/source_to_intent_research_kernel_ingress_evidence_gate.py
examples/first_real_triton_kernel_path.py
examples/source_to_intent_research_source_runtime_smoke.py
examples/source_to_intent_research_readiness.py
examples/external_frontend_package_conformance.py
examples/real_triton_integration_admission_gate.py
examples/source_ingestion_quarantine_gate.py
examples/package_import_sandbox_gate.py
examples/plugin_discovery_allowlist_gate.py
examples/triton_jit_execution_sandbox_gate.py
examples/device_access_sandbox_gate.py
examples/generated_artifact_quarantine_gate.py
examples/source_to_intent_parser_block_gate.py
```

Key docs:

- [Frontend adapter](docs/FRONTEND_ADAPTER.md)
- [Triton source threat model](docs/TRITON_SOURCE_THREAT_MODEL.md)
- [Triton source preflight](docs/TRITON_SOURCE_PREFLIGHT.md)
- [Triton integration readiness](docs/TRITON_INTEGRATION_READINESS.md)
- [Real Triton Integration Admission Gate](docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md)
- [Real Triton Integration Threat Model](docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md)
- [Source Ingestion Quarantine Gate](docs/SOURCE_INGESTION_QUARANTINE_GATE.md)
- [Package Import Sandbox Gate](docs/PACKAGE_IMPORT_SANDBOX_GATE.md)
- [Plugin Discovery Allowlist Gate](docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md)
- [Triton JIT Execution Sandbox Gate](docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md)
- [Device Access Sandbox Gate](docs/DEVICE_ACCESS_SANDBOX_GATE.md)
- [Generated Artifact Quarantine Gate](docs/GENERATED_ARTIFACT_QUARANTINE_GATE.md)
- [Native Backend Execution Security Gate](docs/NATIVE_BACKEND_EXECUTION_SECURITY_GATE.md)
- [Real Triton Surface Gate Completion](docs/REAL_TRITON_SURFACE_GATE_COMPLETION.md)
- [Real Triton First Slice Plan](docs/REAL_TRITON_FIRST_SLICE_PLAN.md)
- [Admitting Source Ingestion RFC](docs/ADMITTING_SOURCE_INGESTION_RFC.md)
- [CI Replay For Admitted Slice](docs/CI_REPLAY_FOR_ADMITTED_SLICE.md)
- [Source Ingestion Approval Criteria](docs/SOURCE_INGESTION_APPROVAL_CRITERIA.md)
- [Source Ingestion Maintainer Approval Artifact](docs/SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md)
- [Source Ingestion Admission Gate](docs/SOURCE_INGESTION_ADMISSION_GATE.md)
- [Source Ingestion Pre-Claim Acyclicity Gate](docs/SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE.md)
- [First Real Triton Kernel Path](docs/FIRST_REAL_TRITON_KERNEL_PATH.md)
- [Real Triton First Slice Evidence Portfolio](docs/REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO.md)
- [Evidence Graph Acyclicity Gate](docs/EVIDENCE_GRAPH_ACYCLICITY_GATE.md)
- [Bounded Source Buffer API](docs/BOUNDED_SOURCE_BUFFER_API.md)
- [Source Ingestion Sandbox Implementation](docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md)
- [Parser Fuzz Negative Corpus For Admitting Slice](docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md)
- [Source-Free Diagnostics Admission Tests](docs/SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md)
- [Source-To-Intent Plain-Data Output Golden For Admitted Slice](docs/SOURCE_TO_INTENT_PLAIN_DATA_OUTPUT_GOLDEN_FOR_ADMITTED_SLICE.md)
- [Source-To-Intent next syntax slice](docs/SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md)
- [External frontend package conformance](docs/EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE.md)
- [Source Intent schema](docs/SOURCE_INTENT_SCHEMA.md)
- [Source Intent axis attributes](docs/SOURCE_INTENT_AXIS_ATTRIBUTES.md)
- [Source Intent frontend conformance gate](docs/SOURCE_INTENT_FRONTEND_CONFORMANCE_GATE.md)
- [Source Intent return semantics](docs/SOURCE_INTENT_RETURN_SEMANTICS.md)
- [Source Intent runtime returns](docs/SOURCE_INTENT_RUNTIME_RETURNS.md)
- [Source-to-Intent corpus evidence](docs/SOURCE_TO_INTENT_CORPUS.md)
- [Source-to-Intent property corpus](docs/SOURCE_TO_INTENT_PROPERTY_CORPUS.md)
- [Source-to-Intent parser report](docs/SOURCE_TO_INTENT_PARSER_REPORT.md)
- [Source-to-Intent research parser](docs/SOURCE_TO_INTENT_RESEARCH_PARSER.md)
- [Source-to-Intent research parser conformance gate](docs/SOURCE_TO_INTENT_RESEARCH_PARSER_CONFORMANCE_GATE.md)
- [Source-to-Intent research diagnostics](docs/SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS.md)
- [Source-to-Intent research preflight bridge](docs/SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE.md)
- [Source-to-Intent research execution bridge](docs/SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE.md)
- [Source-to-Intent research idiom alignment](docs/SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT.md)
- [Source-to-Intent research evidence gate](docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md)
- [Source-to-Intent research proof bundle](docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md)
- [Kernel Ingress runtime output closure index](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX.md)
- [Kernel Ingress Runtime Replay Verifier Index](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX.md)
- [Source-to-Intent research capability claim](docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md)
- [Source-to-Intent research capability claim gate](docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE.md)
- [Source-to-Intent research source runtime smoke](docs/SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE.md)
- [Source-to-Intent research kernel ingress](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md)
- [Source-to-Intent research kernel ingress runtime matrix](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX.md)
- [Source-to-Intent research kernel ingress runtime step trace](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE.md)
- [Source-to-Intent research kernel ingress runtime evidence bundle index](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX.md)
- [Source-to-Intent research kernel ingress backend equivalence](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md)
- [Source-to-Intent research kernel ingress backend equivalence shape profiles](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md)
- [Source-to-Intent research kernel ingress workload scope](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE.md)
- [Source-to-Intent research kernel ingress runtime coverage policy](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY.md)
- [Source-to-Intent research kernel ingress runtime backend alignment](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT.md)
- [Source-to-Intent research kernel ingress boundary budget](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET.md)
- [Source-to-Intent research kernel ingress rejection coverage](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE.md)
- [Source-to-Intent research kernel ingress conformance gate](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE.md)
- [Source-to-Intent research kernel ingress diagnostics](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS.md)
- [Source-to-Intent research kernel ingress idiom alignment](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT.md)
- [Source-to-Intent research kernel ingress proof bundle](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md)
- [Source-to-Intent research kernel ingress evidence gate](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md)
- [First Real Triton Kernel Path](docs/FIRST_REAL_TRITON_KERNEL_PATH.md)
- [Real Triton First Slice Evidence Portfolio](docs/REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO.md)
- [Source-to-Intent parser block gate](docs/SOURCE_TO_INTENT_PARSER_BLOCK_GATE.md)
- [Source-to-Intent research readiness](docs/SOURCE_TO_INTENT_RESEARCH_READINESS.md)
- [Source-to-Intent parser gate](docs/SOURCE_TO_INTENT_PARSER_GATE.md)

## Backend Authoring

Backends enter TUC as capability data first. Backend execution is allowed only
through explicitly trusted prototype executors.

Current authoring path:

```text
manifest
    -> Manifest Claim Review
    -> Backend Capability Coverage
    -> Backend Registry diagnostics
    -> Compiler decision report
    -> Backend conformance
    -> Backend Author Readiness
```

The portable, data-only Backend Integration Package v0 now closes the
capability-and-planning portion of the external backend author test. Run
`examples/backend_integration_package.py` against the reference package
`examples/backend_packages/external_vector.v0.json`. The contract and evidence
are documented in `docs/BACKEND_INTEGRATION_PACKAGE.md`, specified by
`schemas/backend_integration_package.v0.schema.json` and
`schemas/backend_integration_package_report.v0.schema.json`, frozen at
`tests/golden/backend_integration_package/external_vector_report.json`, and
accepted by `rfcs/0282-backend-integration-package.md`. No backend code is
loaded and a passing report grants no execution permission.

Objective Gamma now verifies that same contract as an installed product
surface: `tuc.integration` and `tuc-backend-verify` are exercised by the
standalone `integration/objective_gamma` consumer against a built wheel outside
the source tree. See
[Objective Gamma External Integration](docs/OBJECTIVE_GAMMA_EXTERNAL_INTEGRATION.md)
and [RFC 0291](rfcs/0291-objective-gamma-external-integration.md). This extends
capability-and-planning portability only; executable plugins remain blocked.

Objective Delta extends the installed product boundary through one complete
bounded semantic proof. The public `tuc.portable_compute` API and
`tuc-prove-portable-compute` CLI accept fixed Source Intent plus both external
data-only packages, preserve their no-fallback source plan, project only to
reviewed trusted simulators, and require layout conversion, correctness, and
backend equivalence before emitting a digest-only PASS. See
[Objective Delta Installed Portable Compute](docs/OBJECTIVE_DELTA_INSTALLED_PORTABLE_COMPUTE.md)
and [RFC 0292](rfcs/0292-objective-delta-installed-portable-compute.md).
External package code, plugins, native artifacts, devices, and performance
claims remain blocked.

Backend Package Execution Admission v0 provides the first controlled bridge.
The digest-bound proof in `examples/backend_package_execution_proof.py`
preserves `reference-cpu -> external-vector`, projects it to
`reference-cpu -> vector-sim`, executes it, and requires Backend Equivalence.
Its contract is documented by
`docs/BACKEND_PACKAGE_EXECUTION_ADMISSION.md`,
`schemas/backend_package_execution_admission_report.v0.schema.json`,
`schemas/backend_package_execution_proof_report.v0.schema.json`,
`tests/golden/backend_package_execution/admission_report.json`,
`tests/golden/backend_package_execution/proof_report.json`, and
`rfcs/0283-backend-package-execution-admission.md`.

Backend Package Execution Portfolio v0 now removes the implicit fallback from
the candidate path. `examples/backend_package_execution_portfolio.py` composes
the existing vector package with
`examples/backend_packages/external_systolic.v0.json`, plans
`external-systolic -> external-vector`, retains the explicit
`blocked -> row_major` layout conversion, projects to
`systolic-sim -> vector-sim`, and passes equivalence against `reference-cpu`.
The complete evidence set is
`docs/BACKEND_PACKAGE_EXECUTION_PORTFOLIO.md`,
`schemas/backend_package_execution_portfolio_report.v0.schema.json`,
`tests/golden/backend_integration_package/external_systolic_report.json`,
`tests/golden/backend_package_execution_portfolio/proof_report.json`, and
`rfcs/0284-multi-package-execution-portfolio.md`.

Package implementations, external plugins, native artifacts, and physical
devices remain unexecuted.

Source Intent Backend Package Portfolio v0 joins that package proof to the
frontend boundary in one live path. The evidence set is
`docs/SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO.md`,
`examples/source_intent_backend_package_portfolio.py`,
`schemas/source_intent_backend_package_portfolio_report.v0.schema.json`,
`tests/golden/frontend/source_intent_backend_package_portfolio_report.json`,
and `rfcs/0285-source-intent-backend-package-portfolio.md`. Source payloads,
raw values, package code, plugins, devices, and native artifacts remain outside
the serialized proof and executable trust boundary.

Triton Research Backend Package Portfolio v0 extends the same path to the
fixed realistic Kernel Ingress source slice. Its complete evidence set is
`docs/TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO.md`,
`examples/triton_research_backend_package_portfolio.py`,
`schemas/triton_research_backend_package_portfolio_report.v0.schema.json`,
`tests/golden/frontend/triton_research_backend_package_portfolio_report.json`,
and `rfcs/0286-triton-research-backend-package-portfolio.md`. The source is
bounded and parsed as AST data; imports, decorators, JIT, package code, plugins,
native artifacts, and devices are not executed.

Current plugin lifecycle boundary:

```bash
python examples/backend_plugin_lifecycle_policy.py
```

This policy keeps external plugin discovery, generated artifact execution, and
native plugin ABI loading blocked. The sandbox model, artifact provenance,
resource budget, fuzz/negative-test evidence, and maintainer approval now exist
as data-only evidence; the lifecycle evidence gate is complete without enabling
execution.

Key docs:

- [Backend API v0.1](docs/BACKEND_API.md)
- [Backend capability schema](docs/BACKEND_CAPABILITY_SCHEMA.md)
- [Backend capability coverage](docs/BACKEND_CAPABILITY_COVERAGE.md)
- [Manifest Claim Review](docs/MANIFEST_CLAIM_REVIEW.md)
- [Backend Author Evidence Gate](docs/BACKEND_AUTHOR_EVIDENCE_GATE.md)
- [Backend Plugin Lifecycle Policy](docs/BACKEND_PLUGIN_LIFECYCLE_POLICY.md)
- [Backend Plugin Sandbox Model](docs/BACKEND_PLUGIN_SANDBOX_MODEL.md)
- [Backend Plugin Artifact Provenance](docs/BACKEND_PLUGIN_ARTIFACT_PROVENANCE.md)
- [Backend Plugin Resource Budget](docs/BACKEND_PLUGIN_RESOURCE_BUDGET.md)
- [Backend Plugin Fuzz Negative Tests](docs/BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS.md)
- [Backend Plugin Maintainer Approval](docs/BACKEND_PLUGIN_MAINTAINER_APPROVAL.md)

## Performance Boundaries

TUC currently proves correctness and inspectability, not native performance
parity.

Native performance claims remain blocked even though the current Kernel Ingress
proof slice now has accepted executable-backend security review metadata.
Existing Kernel Ingress governance, policy, scope, methodology, provenance,
comparison, planner, break-even, leaky-abstraction, benchmark artifact
inventory, executable-surface review, and golden evidence remain review
metadata, not a native performance proof.

Current readiness evidence marks accepted, digest-pinned performance RFC,
threshold-policy, acceptance-criteria, benchmark artifact manifest metadata,
and executable-backend security review metadata present, along with
Kernel-Ingress-derived workload scope, break-even workload estimates, benchmark
methodology, native-baseline provenance candidates, blocked native comparison
metadata, digest-bound versioned toolchain environment evidence, correctness
goldens, planner-overhead phase separation, leaky-abstraction boundary evidence,
runtime-plan goldens, compiler-decision goldens, and the fail-closed baseline
benchmark report schema. Readiness can be metadata-complete while native
performance claims stay blocked. The Performance Proof Interpretation report is
the next gate: it records that readiness is true while accepted measurement
interpretation artifacts are still not supplied.

The planner-overhead portfolio evidence is generated by
`examples/planner_overhead_portfolio.py` and documented in
`docs/PLANNER_OVERHEAD_PORTFOLIO.md`.

Key docs:

- [Performance proof boundary](docs/PERFORMANCE_PROOF_BOUNDARY.md)
- [Performance proof readiness](docs/PERFORMANCE_PROOF_READINESS.md)
- [Performance proof interpretation](docs/PERFORMANCE_PROOF_INTERPRETATION.md)
- [Planner overhead report](docs/PLANNER_OVERHEAD_REPORT.md)
- [Planner overhead portfolio](docs/PLANNER_OVERHEAD_PORTFOLIO.md)
- [Leaky abstraction report](docs/LEAKY_ABSTRACTION_REPORT.md)
- [Executable backend security review](docs/EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md)
- [Backend Plugin Lifecycle Policy](docs/BACKEND_PLUGIN_LIFECYCLE_POLICY.md)
- [Backend Plugin Sandbox Model](docs/BACKEND_PLUGIN_SANDBOX_MODEL.md)
- [Backend Plugin Artifact Provenance](docs/BACKEND_PLUGIN_ARTIFACT_PROVENANCE.md)
- [Backend Plugin Resource Budget](docs/BACKEND_PLUGIN_RESOURCE_BUDGET.md)
- [Backend Plugin Fuzz Negative Tests](docs/BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS.md)
- [Backend Plugin Maintainer Approval](docs/BACKEND_PLUGIN_MAINTAINER_APPROVAL.md)

## Governance

TUC is pre-alpha. APIs, IR names, backend contracts, and runtime behavior are
expected to change as the project moves from prototype proof toward a stable
hardware-independent compute interface.

Project controls:

- Apache-2.0 license.
- RFC process for architecture changes.
- CODEOWNERS-backed review boundaries.
- Branch protection guidance.
- CI, security scanning, SBOM/checksum release artifacts, and Trusted
  Publishing governance.
- Deterministic Objective Delta reproduction kit and receipt with release
  attestations and an explicit no-independent-reproduction claim.

Key docs:

- [Contributing](CONTRIBUTING.md)
- [Governance](GOVERNANCE.md)
- [Security baseline](docs/SECURITY_BASELINE.md)
- [Review policy](docs/REVIEW_POLICY.md)
- [Release governance](docs/RELEASE_GOVERNANCE.md)
- [OCI source-worker release provenance](docs/OCI_SOURCE_WORKER_RELEASE_PROVENANCE.md)
- [Objective Delta Reproduction Kit](docs/OBJECTIVE_DELTA_REPRODUCTION_KIT.md)
- [Independent Reproduction Outreach](docs/INDEPENDENT_REPRODUCTION_OUTREACH.md)
- [Branch protection policy](docs/BRANCH_PROTECTION.md)

## Quickstart

```powershell
docker compose build dev
docker compose run --rm dev bash
```

```bash
pytest -q
python examples/proof_of_execution.py
```

## Repository Layout

```text
docs/       Project documentation
examples/   Runnable prototype examples
rfcs/       Design proposals and accepted decisions
src/tuc/    TUC Python package
tests/      Unit and golden tests
```

## License

TUC is licensed under the [Apache License 2.0](LICENSE).
