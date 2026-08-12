# TUC Master Plan

## The Universal Compute

Adaptive strategic master plan

Version: Living document

Status: Active

This document is the strategic north star for TUC. When roadmap items,
implementation ideas, or backend proposals conflict with this plan, this plan
wins until it is deliberately revised through the RFC process.

## Mission

TUC exists to explore whether compute intent can become more stable than the
hardware it runs on.

The project aims to create an open, hardware-independent compute layer that can
survive multiple generations of accelerator architectures.

The goal is not to build another compiler.

The goal is to reduce dependency on proprietary software stacks that emerge
with every new hardware generation.

## Core Thesis

Historically:

```text
New Hardware
    ->
New SDK
    ->
New Compiler
    ->
New Runtime
    ->
New Lock-In
```

TUC explores an alternative:

```text
Compute Intent
        ->
The Universal Compute
        ->
Capability Description
        ->
Runtime Planning
        ->
Hardware
```

Hardware should describe capabilities.

Software should describe intent.

TUC should perform the translation.

## Strategic Identity

TUC is not:

- a CUDA competitor
- a Triton fork
- a GPU compiler
- a benchmark project
- an optimization project

TUC is:

- a compute abstraction layer
- a hardware capability framework
- a runtime planning system
- an execution orchestration layer
- an experiment in hardware independence

## Research Claim Boundary

TUC's near-term objective is not to replace CUDA, ROCm, XLA, TVM, IREE, MLIR,
or production vendor compiler stacks.

The research objective is narrower and falsifiable: prove that a
hardware-independent compute interface can preserve source intent, expose
capability-driven planning decisions, and attach enough evidence that frontend
intake, runtime execution, and performance-boundary claims can be reviewed
without trusting opaque backend behavior.

Open proof obligations include:

- a narrow Source-to-Intent parser that turns caller-provided source buffers
  into `source_intent.v0` plain data without importing, evaluating decorators,
  executing `@triton.jit`, or producing `ComputeGraph` directly
- leaky-abstraction evidence showing which performance facts stay outside
  HAC-IR and which backend decisions are allowed in HS-IR/runtime planning
- planner-overhead and performance-boundary evidence before any native
  performance claim is accepted
- external review and conformance evidence before claiming ecosystem
  compatibility

The narrow Source-to-Intent obligation now has a stronger research prototype:
one realistic bounded module is parsed in a fixed, resource-limited Linux
worker, independently revalidated in the parent, and carried through the
no-fallback Systolic/Vector package portfolio with reference correctness and
backend equivalence. This closes process isolation for the current research
slice, not production admission. Filesystem namespaces, kernel network
isolation, syscall filtering, broader parser coverage, and independent
security approval remain open before any production source-ingestion claim.

The current narrow slice now also crosses a dedicated OCI boundary with
kernel-observed network and filesystem isolation, seccomp,
no-new-privileges, zero capabilities, non-root identity, and cgroup limits.
Its Source Intent digest is bound to the no-fallback Systolic/Vector execution
proof. This establishes a practical kernel-isolated research path while
retaining an explicit boundary: published image provenance, independent
security review, broader syntax coverage, and production admission are not yet
claimed.

The protected release path now builds the same worker as a `linux/amd64` OCI
Image Layout archive, verifies its descriptor graph and fixed non-root runtime
configuration without extraction, generates a dedicated CycloneDX SBOM, and
configures GitHub OIDC provenance and SBOM attestations. The same GitHub-hosted
run must independently execute GitHub CLI verification against a policy-bound
repository, signer workflow, commit, ref, issuer, predicate, and runner class,
then emit a bounded receipt. This closes release-path verification readiness
for the research artifact. An executed protected release run, external
consumer verification, public registry publication, production source
ingestion, and a production sandbox remain outside the claim.

## Non-Negotiable Principles

### Principle 1

Hardware neutrality is more important than hardware support.

If a hardware-specific optimization damages neutrality, reject it.

### Principle 2

The abstraction layer is more valuable than any individual backend.

Protect HAC-IR.

### Principle 3

Capabilities matter more than implementations.

TUC reasons about what hardware can do, not how hardware does it.

### Principle 4

Every generation of hardware should be able to integrate without redesigning
TUC.

### Principle 5

Proofs are more important than plans.

Working demonstrations outrank architecture documents.

## Strategic Assets

### Asset A: HAC-IR

Purpose: represent compute intent independently of hardware.

Requirements:

- deterministic
- inspectable
- stable
- hardware-neutral

### Asset B: Backend Capability Model

Purpose: allow hardware to describe itself.

Never force hardware-specific assumptions into HAC-IR.

### Asset C: Runtime Planning

Purpose: determine:

- where work executes
- why work executes there
- movement costs
- execution costs
- error implications

### Asset D: Open Integration Layer

Purpose: reduce the cost of integrating future hardware.

## Adaptive Development Framework

Before every feature, ask:

```text
Does this increase hardware independence?
```

If no, deprioritize.

Then ask:

```text
Does this strengthen HAC-IR?
```

If no, require strong justification.

Then ask:

```text
Would a future hardware vendor benefit from this?
```

If no, question whether it belongs in the core.

## Critical Success Metrics

Do not measure:

- GitHub stars
- followers
- social media reach
- sponsorships

Measure:

- abstraction quality
- backend onboarding effort
- runtime planning quality
- hardware neutrality
- proof milestones

## The Proof Ladder

Every development cycle should move one level upward.

### Level 0: Architecture

Question: can the concept be described?

### Level 1: Prototype

Question: can the concept be implemented?

### Level 2: Proof

Question: can the concept work?

### Level 3: Validation

Question: can another person reproduce it?

### Level 4: Integration

Question: can another developer extend it?

### Level 5: Adoption

Question: can another organization use it?

## Current Strategic Objective

### Objective Alpha

Build the smallest unarguable proof.

Target:

```text
Graph
    ->
HAC-IR
    ->
Runtime Planning
    ->
Backend A
    ->
Backend B
    ->
Correct Result
```

Success means mathematical correctness, not performance.

Native performance parity is a later proof class. It requires separate leaky-
abstraction evidence, planner-overhead evidence, native baseline provenance,
benchmark methodology, benchmark artifacts, and executable-backend security
review before TUC may claim competitive hardware speed. Until those exist, the
Performance Proof Readiness report remains blocked.

## Critical Milestones

### Milestone 1: Proof Of Abstraction

Required artifact:

```text
examples/proof_of_abstraction.py
```

Output:

- Proof metadata
- Input graph
- HAC-IR
- Backend assignments
- Transfer plan
- Result
- Reference result
- PASS

Validation artifact:

```text
tests/golden/proofs/proof_of_abstraction.txt
```

Additional Objective Alpha proof artifact:

```text
examples/proof_of_reduction.py
```

Validation artifact:

```text
tests/golden/proofs/proof_of_reduction.txt
```

### Milestone 2: Real Triton Integration

Transition:

```text
Real Triton Kernel
        ->
bounded Source-to-Intent parser
        ->
Source Intent IR
        ->
Frontend Adapter
        ->
HAC-IR
```

After this milestone, TUC becomes significantly more credible as a research
proof. It still does not become a CUDA replacement.

### Milestone 3: Backend Author Test

Question: can an external developer integrate a backend without modifying the
TUC core?

If no, the architecture is not ready.

Current result: **PASS for capability and planning integration; executable
backend admission remains blocked.** The data-only contract is documented in
`docs/BACKEND_INTEGRATION_PACKAGE.md`. The runnable proof
`examples/backend_integration_package.py` consumes the portable reference
package `examples/backend_packages/external_vector.v0.json` without a core
change or plugin import. Its fail-closed contracts are
`schemas/backend_integration_package.v0.schema.json` and
`schemas/backend_integration_package_report.v0.schema.json`; the deterministic
result is frozen at
`tests/golden/backend_integration_package/external_vector_report.json` and the
decision is recorded in `rfcs/0282-backend-integration-package.md`.

This proves the external ownership boundary for capability declaration,
negative conformance, and compiler selection. It does not prove a native ABI,
vendor code execution, device access, or performance.

### Milestone 4: Heterogeneous Execution Proof

Target:

```text
GPU
+
Specialized Backend
```

working together.

Backend Package Execution Admission first proved the transition from one
external capability package to a digest-bound trusted executor projection. Its
historical evidence remains
`docs/BACKEND_PACKAGE_EXECUTION_ADMISSION.md`,
`examples/backend_package_execution_proof.py`,
`schemas/backend_package_execution_admission_report.v0.schema.json`,
`schemas/backend_package_execution_proof_report.v0.schema.json`,
`tests/golden/backend_package_execution/admission_report.json`,
`tests/golden/backend_package_execution/proof_report.json`, and
`rfcs/0283-backend-package-execution-admission.md`.

Backend Package Execution Portfolio now proves the stronger no-fallback
composition path:

```text
external-systolic -> external-vector
        |                  |
        v                  v
  systolic-sim ------> vector-sim
```

The package boundary is exact and data-only, the intermediate
`blocked -> row_major` layout conversion remains explicit, execution uses only
fixed trusted simulators, and Runtime Backend Equivalence passes against the
all-CPU baseline.

Evidence:

`docs/BACKEND_PACKAGE_EXECUTION_PORTFOLIO.md`,
`examples/backend_package_execution_portfolio.py`,
`examples/backend_packages/external_systolic.v0.json`,
`schemas/backend_package_execution_portfolio_report.v0.schema.json`,
`tests/golden/backend_integration_package/external_systolic_report.json`,
`tests/golden/backend_package_execution_portfolio/proof_report.json`, and
`rfcs/0284-multi-package-execution-portfolio.md`.

This materially advances Milestones 3 and 4 but does not close the native
target: external package code, GPU kernels, specialized physical devices, and
native performance remain unexecuted and unproven.

The Source Intent Backend Package Portfolio now closes the frontend-to-package
gap in the same milestone:

```text
Source Intent -> HAC-IR -> external package portfolio
              -> trusted heterogeneous execution
              -> public outputs + reference correctness + equivalence
```

It runs from `examples/source_intent_backend_package_portfolio.py` and is
documented by `docs/SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO.md`, with
`schemas/source_intent_backend_package_portfolio_report.v0.schema.json`,
`tests/golden/frontend/source_intent_backend_package_portfolio_report.json`,
and `rfcs/0285-source-intent-backend-package-portfolio.md`. This is the first
single live proof connecting neutral frontend intent to independently declared
heterogeneous capability ownership without fallback or external code
execution.

The Triton Research Backend Package Portfolio now advances that result from
plain frontend data to the fixed realistic syntax slice:

```text
bounded Triton module text -> Source Intent -> HAC-IR
  -> external package portfolio -> trusted heterogeneous execution
  -> public output + independent correctness + equivalence
```

Evidence is provided by
`docs/TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO.md`,
`examples/triton_research_backend_package_portfolio.py`,
`schemas/triton_research_backend_package_portfolio_report.v0.schema.json`,
`tests/golden/frontend/triton_research_backend_package_portfolio_report.json`,
and `rfcs/0286-triton-research-backend-package-portfolio.md`. Source remains a
bounded research input: module imports, decorators, JIT, external packages, and
native backends are not executed, and production source ingestion remains
unadmitted.

RFC 0287 closes the first source-value semantic gap: the fixed Triton
`tl.where(x > 0, x, 0)` form is represented as neutral
`elementwise_kind=relu`, mapped to the bounded runtime kernel, and checked with
negative-valued inputs against an independent reference. Exact redundant
`tl.where(x > 0, x, x)` is modeled as identity; every other `where` form fails
closed. This keeps the research proof honest without widening source admission.

## Strategic Risks

### Risk A: Becoming Another Compiler

Mitigation: focus on abstraction.

### Risk B: Vendor Capture

Mitigation: keep vendor logic outside HAC-IR.

### Risk C: Architecture Inflation

Mitigation: no architecture without implementation.

### Risk D: Simulator Illusion

Mitigation: require numerical correctness.

### Risk E: Scope Explosion

Mitigation: always pursue the smallest proof.

## Architectural Guardrails

Never hard-code these assumptions inside HAC-IR:

- NVIDIA assumptions
- AMD assumptions
- photonic assumptions
- neuromorphic assumptions

Backend-specific concepts belong in:

- manifests
- capabilities
- backend implementations

They do not belong in:

- HAC-IR semantics
- compiler-neutral passes

## MLIR Relationship

TUC does not compete with MLIR.

TUC may eventually build on MLIR.

Strategic position:

```text
Frontend
    ->
TUC
    ->
MLIR
    ->
Backend
```

MLIR is infrastructure.

TUC is abstraction.

## Long-Term Success Definition

The project succeeds when the following statement becomes true:

> A hardware company concludes that integrating with TUC is faster, cheaper,
> and less risky than building a new compiler and runtime stack from scratch.

At that moment, TUC becomes infrastructure.

## Final Rule

Whenever uncertainty appears, return to the mission:

```text
Compute Intent
        ->
The Universal Compute
        ->
Any Hardware
```

Everything else is implementation detail.
