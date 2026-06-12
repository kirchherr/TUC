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
- Runtime Buffer Lifetime, Allocation Plan, Memory Budget, and Memory Planning
  Gate.
- Runtime Candidate Score Evidence, Policy, Conformance, and Scoring Gate.
- Operation/value contract checks for shapes, `float64`, finite values, and
  MVP operation semantics.

CI-facing runtime evidence entry points:

```text
examples/runtime_evidence_gate.py
examples/runtime_tensor_store_evidence.py
examples/runtime_input_manifest.py
examples/runtime_execution_receipt.py
examples/runtime_execution_evidence_bundle.py
examples/runtime_output_contract.py
examples/runtime_public_output_bundle.py
examples/source_intent_runtime_returns.py
examples/runtime_reference_correctness.py
examples/runtime_candidate_scoring_gate.py
examples/runtime_memory_planning_gate.py
```

Key docs:

- [Runtime Executor](docs/RUNTIME_EXECUTOR.md)
- [Runtime Tensor Store](docs/RUNTIME_TENSOR_STORE.md)
- [Runtime Tensor Store Evidence](docs/RUNTIME_TENSOR_STORE_EVIDENCE.md)
- [Runtime Input Manifest](docs/RUNTIME_INPUT_MANIFEST.md)
- [Runtime Output Manifest](docs/RUNTIME_OUTPUT_MANIFEST.md)
- [Runtime Execution Receipt](docs/RUNTIME_EXECUTION_RECEIPT.md)
- [Runtime Execution Evidence Bundle](docs/RUNTIME_EXECUTION_EVIDENCE_BUNDLE.md)
- [Runtime Output Contract](docs/RUNTIME_OUTPUT_CONTRACT.md)
- [Runtime Public Output Bundle](docs/RUNTIME_PUBLIC_OUTPUT_BUNDLE.md)
- [Runtime Reference Correctness](docs/RUNTIME_REFERENCE_CORRECTNESS.md)
- [Runtime Memory Planning Gate](docs/RUNTIME_MEMORY_PLANNING_GATE.md)
- [Runtime Candidate Scoring Gate](docs/RUNTIME_CANDIDATE_SCORING_GATE.md)
- [Runtime override policy](docs/RUNTIME_OVERRIDE_POLICY.md)

Runtime schemas:

```text
schemas/runtime_input_manifest_report.v0.schema.json
schemas/runtime_execution_receipt_report.v0.schema.json
schemas/runtime_execution_evidence_bundle_report.v0.schema.json
schemas/runtime_output_contract_report.v0.schema.json
schemas/runtime_public_output_bundle_report.v0.schema.json
schemas/source_intent_runtime_returns_report.v0.schema.json
```

## Frontend Intake

TUC does not directly ingest or execute Triton/Python source today.

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
- Source Intent IR, schema, intake, return semantics, conformance, and metadata
  conversion.
- Source Intent Frontend Conformance Gate for CI-facing external frontend
  plain-data and public-return evidence.
- Source Intent Runtime Returns evidence connecting explicit frontend returns
  to runtime public outputs after trusted execution.
- Source-To-Intent Parser Block Gate proving the default source parser path
  remains intentionally closed.
- Source-to-Intent parser gate remains blocked until dedicated parser evidence
  exists.

CI-facing frontend evidence entry points:

```text
examples/source_intent_frontend_conformance_gate.py
examples/source_intent_frontend_conformance.py
examples/source_intent_runtime_returns.py
examples/source_to_intent_parser_block_gate.py
```

Key docs:

- [Frontend adapter](docs/FRONTEND_ADAPTER.md)
- [Triton source threat model](docs/TRITON_SOURCE_THREAT_MODEL.md)
- [Triton source preflight](docs/TRITON_SOURCE_PREFLIGHT.md)
- [Source Intent schema](docs/SOURCE_INTENT_SCHEMA.md)
- [Source Intent frontend conformance gate](docs/SOURCE_INTENT_FRONTEND_CONFORMANCE_GATE.md)
- [Source Intent return semantics](docs/SOURCE_INTENT_RETURN_SEMANTICS.md)
- [Source Intent runtime returns](docs/SOURCE_INTENT_RUNTIME_RETURNS.md)
- [Source-to-Intent parser block gate](docs/SOURCE_TO_INTENT_PARSER_BLOCK_GATE.md)
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
