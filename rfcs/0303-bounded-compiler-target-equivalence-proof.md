# RFC 0303: Bounded Compiler Target Equivalence Proof

## Status

Accepted after the reviewed C11 no-call preflight, controlled static `x86_64`
execution, reference comparison, and two-target aggregate all passed. This RFC
does not admit a native TUC backend.

## Context

RFC 0302 proves one exact path from accepted Source Intent to compiler-emitted
CUDA/SASS and physical `sm_86` execution. That result crosses a real
code-generation boundary, but it remains CUDA-specific. Merely adding more
CUDA syntax or another NVIDIA architecture would not test whether the Source
Intent boundary is independent of that compiler target.

The next bounded research question is:

> Can the identical accepted Source Intent and public workload be lowered into
> a separately specified non-CUDA artifact, execute through a different
> mechanism, and retain terminal reference semantics?

## Decision

Add an exact-match C11 target for the canonical RFC 0302 float32 `4 x 8` by
`8 x 2` Matmul followed by explicit ReLU. The C11 emitter reuses the same
strict Source Intent and workload acceptance boundary and emits:

- a metadata-only lowering plan;
- a fixed public workload header;
- one generated header and one translation unit containing exactly two fixed
  C11 function definitions.

Compile the generated unit and a separate harness ahead of time with a
digest-pinned GCC 14.2.0 builder. The build must produce a static `x86_64` ELF,
reject dynamic dependencies, verify the two generated symbols, and copy only
the executable plus provenance metadata into a `scratch` runtime image.

Run a no-call preflight and a controlled execution under a dedicated Compose
profile with no network, mount, device, GPU, dynamic loader, runtime compiler,
or shell. Execution may call exactly the two fixed generated functions and use
exactly 256 bytes of stack-resident workload data. A separately implemented
reference loop must validate the terminal result.

Finally, add a closed metadata-only aggregate which first validates the
accepted RFC 0302 GPU report and the new C11 report, then binds their identical
Source Intent and workload provenance and their reference-correctness PASS.

## Security Boundary

All JSON and worker output are untrusted data. Strict UTF-8, duplicate-key and
non-finite-number rejection, byte/depth/item limits, symlink rejection,
canonical digests, typed Source Intent validation, exact semantic checks, and
exact-key worker validation apply before a claim can pass.

Generated code uses fixed templates and identifiers. Caller data cannot become
C syntax, include paths, compiler options, commands, imports, or runtime code.
Checked-in generated artifacts must equal fresh emission byte for byte and are
bound through build arguments, OCI labels, image inspection, and report
provenance.

The runtime image is static and contains no writable host path or device
surface. It runs as UID/GID 10001 with a read-only root filesystem, no network,
no mounts, no devices, all capabilities dropped, no-new-privileges, seccomp,
private IPC, one CPU, 128 MiB memory, eight PIDs, 4 MiB shared memory, bounded
output, and a 20 second deadline.

## Claim Boundary

A passing aggregate establishes only:

> One exact, previously admitted Source Intent and fixed public workload were
> deterministically lowered into reviewed CUDA/SASS and static C11 artifacts;
> both same-maintainer observations executed through their bounded mechanisms
> and matched the same terminal reference semantics.

It does not establish arbitrary source support, arbitrary Source Intent,
cross-ISA portability, cross-vendor accelerator execution, general CPU or CUDA
backends, runtime code generation, normal-runtime native admission, native
performance parity, production safety, universal hardware support, vendor
replacement, or independent reproduction.

The result demonstrates a second compiler target, not a second instruction-set
architecture portability result: the CUDA observation is `sm_86`, and the C11
observation is one static `x86_64` ELF. Both are maintained and observed by the
same project owner.

## Evidence

- C11 emitter: `examples/bounded_compiler_emitted_c11_emission.py`;
- C11 orchestrator: `examples/bounded_compiler_emitted_c11_proof.py`;
- target aggregate: `examples/bounded_compiler_target_equivalence_proof.py`;
- fixed C11 build inputs: `docker/c11-observation/`;
- C11 schema:
  `schemas/bounded_compiler_emitted_c11_observation_report.v0.schema.json`;
- target aggregate schema:
  `schemas/bounded_compiler_target_equivalence_proof.v0.schema.json`;
- accepted C11 observation:
  `tests/golden/proofs/bounded_compiler_emitted_c11_observation_report.json`;
- accepted aggregate:
  `tests/golden/proofs/bounded_compiler_target_equivalence_proof.json`;
- tests: `tests/test_bounded_compiler_target_equivalence_proof.py`;
- procedure: `docs/BOUNDED_COMPILER_TARGET_EQUIVALENCE_PROOF.md`;
- threat model: `docs/BOUNDED_COMPILER_EMITTED_C11_THREAT_MODEL.md`.

## Consequences

This replaces a CUDA-only compiler-emission argument with a bounded two-target
argument while leaving every normal execution gate closed. It demonstrates
that hardware-specific details can remain in target emitters and build
contracts without entering the accepted Source Intent payload.

The cost is deliberate duplication and narrowness. A new operation, shape,
dtype, ISA, compiler, execution host, native-runtime integration, or dynamic
input policy requires a successor decision and new negative/security evidence.
Independent reproduction remains the strongest external evidence obligation.
