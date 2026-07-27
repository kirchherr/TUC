# Minimal TUC Walkthrough

This walkthrough is the shortest current path through the TUC research claim:
a hardware-independent compute intent can be planned, executed through trusted
prototype backends, and reviewed through bounded evidence.

It is intentionally small. It does not claim native execution, native
performance parity, broad Triton compatibility, or general source-code parsing.

## Core Path

```text
Compute intent
  -> HAC-IR / Source Intent research fixture
  -> capability-driven runtime plan
  -> trusted in-process Runtime Executor
  -> Runtime Tensor Store
  -> Output Contract and Public Output Bundle
  -> Reference Correctness
  -> Runtime Evidence Bundle
  -> Runtime Replay Verifier
  -> Backend Equivalence
  -> Transfer and Layout Trace Evidence
  -> Evidence Gate
```

## Fast Read Order

Start with these files:

1. `TUC_MASTER_PLAN.md`
2. `docs/RUNTIME_EVIDENCE_FLOW.md`
3. `docs/PROOF_OF_BACKEND_EQUIVALENCE.md`
4. `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md`
5. `docs/PERFORMANCE_PROOF_BOUNDARY.md`

This order keeps the project centered on the research proof instead of making
the README carry every detail.

## Minimal Commands

From the repository root:

```bash
python examples/proof_of_execution.py
python examples/proof_of_backend_equivalence.py
python examples/source_intent_mixed_runtime_public_proof_bundle.py
python examples/runtime_evidence_gate.py
python examples/source_to_intent_research_kernel_ingress_evidence_gate.py
python examples/first_real_triton_kernel_path.py
```

With the Docker development environment:

```bash
docker compose run --rm dev python examples/proof_of_execution.py
docker compose run --rm dev python examples/proof_of_backend_equivalence.py
docker compose run --rm dev python examples/source_intent_mixed_runtime_public_proof_bundle.py
docker compose run --rm dev python examples/runtime_evidence_gate.py
docker compose run --rm dev python examples/source_to_intent_research_kernel_ingress_evidence_gate.py
docker compose run --rm dev python examples/first_real_triton_kernel_path.py
```

The first command demonstrates trusted runtime execution for an already
compiled graph. The second shows the canonical Backend Equivalence proof for
`reference-cpu` versus mixed `systolic-sim + vector-sim` placement. The third
binds Source Intent plain data through mixed trusted execution, Public Output
Bundle, Reference Correctness, and Backend Equivalence in one digest-only proof.
The fourth checks the runtime evidence set. The fifth checks the current
Source-To-Intent Kernel Ingress research slice, including runtime evidence,
replay, backend equivalence, and source-free proof-bundle bindings. The sixth
command is the shortest practical top-level proof for the single `mvp_pipeline`
Kernel Ingress path.

## What To Inspect

Runtime execution evidence:

```text
tests/golden/runtime_execution_evidence_bundle/proof_of_execution.json
tests/golden/runtime_evidence_replay_verifier/proof_of_execution.json
tests/golden/proofs/runtime_evidence_gate.txt
```

Backend equivalence evidence:

```text
tests/golden/runtime_backend_equivalence/current_report.json
tests/golden/runtime_backend_equivalence/vector_sim_report.json
tests/golden/runtime_backend_equivalence/mixed_accelerators.json
tests/golden/proofs/proof_of_backend_equivalence.json
schemas/source_intent_mixed_runtime_public_proof_bundle_report.v0.schema.json
tests/golden/frontend/source_intent_mixed_runtime_public_proof_bundle.json
tests/golden/frontend/source_to_intent_research_kernel_ingress_backend_equivalence.json
tests/golden/frontend/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.json
```

Transfer and layout-boundary evidence:

Runtime Transfer Trace Index and Runtime Layout Conversion Trace Index artifacts
show where planned movement and `blocked -> row_major` layout conversion align
to producer and consumer runtime trace steps.

```text
tests/golden/runtime_transfer_trace_index/current_report.json
tests/golden/runtime_transfer_trace_replay_verifier/current_report.json
tests/golden/runtime_layout_conversion_trace_index/current_report.json
tests/golden/runtime_layout_conversion_trace_replay_verifier/current_report.json
tests/golden/runtime_backend_equivalence_layout_binding/current_report.json
```

Kernel Ingress research proof evidence:

```text
tests/golden/frontend/source_to_intent_research_kernel_ingress_proof_bundle.json
tests/golden/frontend/source_to_intent_research_kernel_ingress_evidence_gate.txt
tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.json
tests/golden/frontend/first_real_triton_kernel_path.json
tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json
schemas/first_real_triton_kernel_path_report.v0.schema.json
schemas/real_triton_first_slice_evidence_portfolio_report.v0.schema.json
```

First Real Triton Kernel Path and portfolio docs:

```text
docs/FIRST_REAL_TRITON_KERNEL_PATH.md
docs/REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO.md
rfcs/0272-first-real-triton-kernel-path.md
rfcs/0274-real-triton-first-slice-evidence-portfolio.md
examples/real_triton_first_slice_evidence_portfolio.py
```

## What This Proves

- The current compute intent fixtures can execute through the fixed trusted
  Runtime Executor registry.
- Runtime values are represented as internal `RuntimeValueRecord` metadata with
  planned backend, planned memory domain, planned layout, and placement source.
- Public review artifacts omit raw tensor values by policy.
- A neutral `reference-cpu` baseline can be compared with capability-selected
  trusted simulator placements such as `linear-sim` and `vector-sim`.
- Planned transfer and `blocked -> row_major` layout-conversion boundaries are
  linked to producer and consumer runtime trace steps without materializing
  transfer or converter steps.
- Evidence gates bind report digests, schema versions, artifact IDs, backend
  sequences, output contracts, and raw-value omission policy.
- Source Intent plain data can now be reviewed through a mixed
  `systolic-sim + vector-sim` public proof bundle.
- Kernel Ingress research cases can be reviewed through Source Intent and
  runtime evidence without treating source preflight as a production parser.

See [Source Intent Mixed Runtime Public Proof Bundle](SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE.md).
Canonical doc path: `docs/SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE.md`.

## What This Does Not Prove

- It does not prove native GPU, TPU, NPU, photonic, analog, or vendor-library
  execution.
- It does not prove native performance parity or a fixed percentage of CUDA,
  HIP, XLA, TVM, IREE, or vendor compiler performance.
- It does not approve arbitrary source-code parsing or execution of
  `@triton.jit`.
- It does not prove real device residency, physical memory placement, stream
  behavior, layout-converter execution, transfer execution, or allocation
  handles.
- It does not authorize plugin discovery, dynamic imports, dynamic libraries,
  generated-code execution, subprocesses, network access, or device access.

## Security Boundary

All public evidence in this walkthrough is metadata-only. Source, IR, manifest,
runtime, and evidence inputs remain untrusted unless they pass the relevant
schema, conformance, and gate checks. Unsupported operations, unknown layouts,
unexpected backend claims, raw-value leakage, implicit layout conversions, and
implicit executable surfaces must fail closed.

The walkthrough is therefore a research proof path, not a shortcut around the
secure compiler boundary.
