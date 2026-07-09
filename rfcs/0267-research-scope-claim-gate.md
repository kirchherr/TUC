# RFC 0267: Research Scope Claim Gate

Status: accepted

## Context

TUC's current goal is to prove that hardware-independent compute intent can be
represented, planned through backend capabilities, executed by trusted
prototype backends, and checked against reference semantics.

External reviews correctly point out that replacing CUDA, ROCm, XLA, TVM, IREE,
or production compiler infrastructure would be a much larger multi-year effort.
TUC should not blur that boundary while building research evidence.

## Decision

Add a project-level Research Scope Claim Gate:

- module: `src/tuc/research_scope_claim_gate.py`
- example: `examples/research_scope_claim_gate.py`
- schema: `schemas/research_scope_claim_gate_report.v0.schema.json`
- golden: `tests/golden/proofs/research_scope_claim_gate.json`
- docs: `docs/RESEARCH_SCOPE_CLAIM_GATE.md`

The gate binds these current top-level evidence artifacts by digest:

- `objective_alpha_research_claim_gate`
- `source_to_intent_research_capability_claim_gate`
- `performance_proof_interpretation`
- `source_ingestion_admission_gate`

## Required Non-Claims

The gate must keep these booleans false:

- `production_compiler_claim`
- `cuda_replacement_claim`
- `rocm_replacement_claim`
- `xla_replacement_claim`
- `tvm_replacement_claim`
- `iree_replacement_claim`
- `native_performance_claim`
- `real_hardware_backend_execution_claim`
- `arbitrary_source_ingestion_claim`
- `arbitrary_third_party_backend_execution_claim`
- `generated_artifact_execution_claim`
- `external_plugin_execution_claim`
- `source_ingestion_admitted`

It also records `time_horizon_claim = no_timeline_claim`.

## Security

The gate is data-only. It validates metadata produced by existing gates and
hashes the serialized reports. It must not parse source, execute source,
import packages, discover plugins, run generated artifacts, access devices,
load native libraries, call subprocesses, or serialize raw tensor values,
runtime handles, host paths, device IDs, source bodies, backend artifacts, or
benchmark samples.

## Consequences

TUC's current high-level claim becomes reviewable as a narrow research proof.
Any future move toward production compiler claims, native hardware execution,
or source ingestion requires a separate admitting gate and evidence trail.
