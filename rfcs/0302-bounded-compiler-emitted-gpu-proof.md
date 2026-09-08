# RFC 0302: Bounded Compiler-Emitted GPU Proof

## Status

Proposed pending successful no-kernel preflight and physical observation on the
reviewed `sm_86` profile. This RFC does not admit a native TUC backend.

## Context

RFCs 0300 and 0301 prove that hand-reviewed fixed CUDA probes can execute one
neutral workload on physical `sm_70` and `sm_86` devices. They deliberately
block compiler-emitted CUDA, so they do not yet prove that accepted compute
intent can cross a code-generation boundary.

The next bounded research question is:

> Can one already admitted `source_intent.v0` Matmul-plus-ReLU program be
> lowered deterministically into reviewed CUDA, compiled ahead of time for one
> fixed GPU class, executed under the existing hardened observation boundary,
> and checked against an independent CPU reference?

## Decision

Add an exact-match compiler-emission experiment for the existing accepted
Triton research slice. The emitter accepts only the canonical Source Intent
payload digest for a fixed `4 x 8` by `8 x 2` float32 Matmul followed by an
explicit ReLU. It emits:

- a metadata-only lowering plan;
- a fixed public workload header;
- exactly two CUDA kernel definitions with fixed symbols.

The emitter performs no file writes, subprocess calls, imports from caller
data, dynamic loading, source execution, device access, or runtime code
generation. Checked-in artifacts must equal fresh emission byte for byte.

The CUDA harness contains no kernel definitions. It may launch only the two
generated fixed symbols, allocate exactly 256 bytes, use one `sm_86` device,
and compare the terminal output with a separately implemented CPU
Matmul-plus-ReLU reference.

The new observation profile is statically allowlisted but is rejected by the
legacy fixed-probe report and CLI paths. It has its own entrypoint, worker
protocol, Compose service, image identity, report schema, proof contract, and
orchestrator.

## Security Boundary

All JSON inputs are untrusted data. Before lowering they are subject to strict
UTF-8 decoding, duplicate-key and non-finite-number rejection, maximum byte,
depth, and item budgets, canonical digest matching, typed Source Intent
validation, and exact semantic checks.

The build context is an exact allowlist. Every input file is bound by a build
argument digest and image label. The image is digest-pinned, emits SASS only
for `sm_86`, contains no PTX, and disables JIT and CUDA cache use.

Runtime retains the RFC 0301 controls: one logical GPU, NVIDIA `compute`
capability only, no network or host mount, read-only root filesystem, non-root
UID/GID 10001, dropped capabilities, no-new-privileges, seccomp, private IPC,
one CPU, 1 GiB memory, 32 PIDs, bounded tmpfs and output, and a 30 second worker
deadline. Physical execution additionally requires explicit current-driver
attestation and shared-GPU-risk acknowledgement.

## Claim Boundary

A passing report establishes only:

> One exact, previously admitted Source Intent payload was deterministically
> lowered into two reviewed CUDA kernels before image build; those kernels ran
> on one physical `sm_86` GPU and their terminal float32 result matched an
> independent CPU reference.

It does not establish arbitrary source or Source Intent support, dynamic
shapes or inputs, a general CUDA backend, runtime code generation, normal TUC
runtime admission, cross-vendor portability, native performance parity,
production safety, or independent reproduction.

The experiment changes no `execute_graph()` behavior and does not reinterpret
the Device Access Sandbox Gate or Native Backend Execution Security Gate.

## Evidence

- deterministic emitter: `examples/bounded_compiler_emission.py`;
- dedicated orchestrator:
  `examples/bounded_compiler_emitted_gpu_proof.py`;
- fixed build inputs and generated artifacts: `docker/gpu-observation/`;
- closed schema:
  `schemas/bounded_compiler_emitted_gpu_observation_report.v0.schema.json`;
- accepted physical observation, once completed:
  `tests/golden/proofs/bounded_compiler_emitted_gpu_observation_report.json`;
- tests: `tests/test_bounded_compiler_emitted_gpu_proof.py`;
- procedure: `docs/BOUNDED_COMPILER_EMITTED_GPU_PROOF.md`;
- threat model: `docs/BOUNDED_COMPILER_EMITTED_GPU_THREAT_MODEL.md`.

## Consequences

This closes a meaningful gap between TUC's admitted frontend data and physical
execution without opening a general generated-artifact execution surface. The
cost is intentional narrowness and duplicated static artifacts. A second
Source Intent shape, operation, dtype, target, emitter template, or runtime
integration requires a successor RFC and its own negative/security evidence.

The next research obligation remains independently provenanced reproduction;
same-maintainer execution cannot satisfy it.
