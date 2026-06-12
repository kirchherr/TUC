# TUC

TUC is **The Universal Compute**: an early-stage open-source prototype exploring
whether compute intent can move through a hardware-independent interface into
capability-driven runtime planning and controlled execution.

TUC is not trying to become just another compiler. It is testing whether
software can describe intent, hardware can describe capabilities, and the
translation layer between them can stay inspectable, secure, and portable.

- Strategic north star: [TUC Master Plan](TUC_MASTER_PLAN.md)
- Operational status: [Roadmap Status](docs/ROADMAP_STATUS.md)

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

## Current Proofs

Objective Alpha is the current proof shape:

```text
Graph -> HAC-IR -> Runtime Plan -> Backend A + Backend B -> Correct Result
```

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
- Runtime Reference Correctness v0 for output/reference comparison without
  serialized tensor values.
- Runtime Execution Receipt v0 linking runtime evidence reports by metadata
  digest without serialized tensor values.
- Runtime Execution Evidence Bundle v0 packaging one coherent metadata-only
  execution evidence set for review.
- Runtime Backend Equivalence v0 comparing `reference-cpu` against
  `systolic-sim`, `vector-sim`, and mixed `systolic-sim` plus `vector-sim`
  placements without serialized tensor values, with all proof slices bound into
  the Runtime Evidence Gate.
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
  Manifest, and Memory Planning Gate.
- Runtime Candidate Score Evidence, Policy, Conformance, and Scoring Gate.
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
examples/runtime_backend_equivalence.py
examples/runtime_backend_equivalence_portfolio.py
examples/runtime_backend_equivalence_portfolio_policy.py
examples/runtime_vector_backend_equivalence.py
examples/runtime_mixed_backend_equivalence.py
examples/runtime_hs_ir_plan_alignment.py
examples/runtime_output_contract.py
examples/runtime_public_output_bundle.py
examples/source_intent_runtime_returns.py
examples/runtime_reference_correctness.py
examples/runtime_candidate_scoring_gate.py
examples/runtime_allocation_request_manifest.py
examples/runtime_memory_planning_gate.py
```

Key docs:

- [Runtime Executor](docs/RUNTIME_EXECUTOR.md)
- [Runtime Evidence Flow](docs/RUNTIME_EVIDENCE_FLOW.md)
- [Runtime Tensor Store](docs/RUNTIME_TENSOR_STORE.md)
- [Runtime Tensor Store Evidence](docs/RUNTIME_TENSOR_STORE_EVIDENCE.md)
- [Runtime Input Manifest](docs/RUNTIME_INPUT_MANIFEST.md)
- [Runtime Output Manifest](docs/RUNTIME_OUTPUT_MANIFEST.md)
- [Runtime Execution Receipt](docs/RUNTIME_EXECUTION_RECEIPT.md)
- [Runtime Execution Evidence Bundle](docs/RUNTIME_EXECUTION_EVIDENCE_BUNDLE.md)
- [Runtime Backend Equivalence](docs/RUNTIME_BACKEND_EQUIVALENCE.md)
- [Runtime Backend Equivalence Portfolio](docs/RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO.md)
- [Runtime Evidence Gate Matrix Coverage](docs/RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE.md)
- [Runtime HS-IR Plan Alignment](docs/RUNTIME_HS_IR_PLAN_ALIGNMENT.md)
- [Runtime Output Contract](docs/RUNTIME_OUTPUT_CONTRACT.md)
- [Runtime Public Output Bundle](docs/RUNTIME_PUBLIC_OUTPUT_BUNDLE.md)
- [Runtime Reference Correctness](docs/RUNTIME_REFERENCE_CORRECTNESS.md)
- [Runtime Allocation Request Manifest](docs/RUNTIME_ALLOCATION_REQUEST_MANIFEST.md)
- [Runtime Memory Planning Gate](docs/RUNTIME_MEMORY_PLANNING_GATE.md)
- [Runtime Candidate Scoring Gate](docs/RUNTIME_CANDIDATE_SCORING_GATE.md)
- [Runtime override policy](docs/RUNTIME_OVERRIDE_POLICY.md)

Runtime schemas:

```text
schemas/runtime_input_manifest_report.v0.schema.json
schemas/runtime_execution_receipt_report.v0.schema.json
schemas/runtime_execution_evidence_bundle_report.v0.schema.json
schemas/runtime_backend_equivalence_report.v0.schema.json
schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json
schemas/runtime_backend_equivalence_portfolio_policy_report.v0.schema.json
schemas/runtime_evidence_gate_matrix_coverage_report.v0.schema.json
schemas/runtime_hs_ir_plan_alignment_report.v0.schema.json
schemas/runtime_output_contract_report.v0.schema.json
schemas/runtime_public_output_bundle_report.v0.schema.json
schemas/source_intent_runtime_returns_report.v0.schema.json
schemas/runtime_allocation_request_manifest_report.v0.schema.json
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
examples/source_to_intent_corpus.py
examples/source_to_intent_property_corpus.py
examples/source_to_intent_parser_report.py
examples/source_to_intent_research_parser.py
examples/source_to_intent_research_parser_conformance_gate.py
examples/source_to_intent_research_readiness.py
examples/source_to_intent_parser_block_gate.py
```

Key docs:

- [Frontend adapter](docs/FRONTEND_ADAPTER.md)
- [Triton source threat model](docs/TRITON_SOURCE_THREAT_MODEL.md)
- [Triton source preflight](docs/TRITON_SOURCE_PREFLIGHT.md)
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
    -> Backend Registry diagnostics
    -> Compiler decision report
    -> Backend conformance
    -> Backend Author Readiness
```

Key docs:

- [Backend API v0.1](docs/BACKEND_API.md)
- [Backend capability schema](docs/BACKEND_CAPABILITY_SCHEMA.md)
- [Manifest Claim Review](docs/MANIFEST_CLAIM_REVIEW.md)
- [Backend Author Evidence Gate](docs/BACKEND_AUTHOR_EVIDENCE_GATE.md)

## Performance Boundaries

TUC currently proves correctness and inspectability, not native performance
parity.

Native performance claims remain blocked until the project has accepted
evidence for leaky-abstraction limits, planner overhead, break-even workload
size, native baseline comparison, benchmark artifact digests, benchmark
methodology, and executable-backend security.

Key docs:

- [Performance proof boundary](docs/PERFORMANCE_PROOF_BOUNDARY.md)
- [Performance proof readiness](docs/PERFORMANCE_PROOF_READINESS.md)
- [Planner overhead report](docs/PLANNER_OVERHEAD_REPORT.md)
- [Leaky abstraction report](docs/LEAKY_ABSTRACTION_REPORT.md)
- [Executable backend security review](docs/EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md)

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

Key docs:

- [Contributing](CONTRIBUTING.md)
- [Governance](GOVERNANCE.md)
- [Security baseline](docs/SECURITY_BASELINE.md)
- [Review policy](docs/REVIEW_POLICY.md)
- [Release governance](docs/RELEASE_GOVERNANCE.md)
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
