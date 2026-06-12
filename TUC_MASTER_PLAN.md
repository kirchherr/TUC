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

### Milestone 4: Heterogeneous Execution Proof

Target:

```text
GPU
+
Specialized Backend
```

working together.

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
