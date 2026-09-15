# Bounded Source-To-Target Execution Proof

## Status

Accepted under RFC 0304 after the existing OCI source-ingestion evidence was
cryptographically bound to the accepted CUDA/SASS-versus-C11 target evidence.

Decision: `rfcs/0304-bounded-source-to-target-execution-proof.md`.

## Research Question

RFC 0303 showed that one exact Source Intent retains terminal reference
semantics across two compiler targets. This proof asks whether that Source
Intent can be traced back to one realistic, bounded frontend source case:

> Can inert Triton-shaped module text cross the isolated research parser into
> the exact Source Intent later emitted and executed by both accepted compiler
> targets, without opening general source ingestion or executing the source?

```text
fixed Triton-shaped source buffer
  -> networkless, read-only OCI research worker
  -> source_intent.v0 digest
       |-> compiler-emitted CUDA -> sm_86 SASS -> physical GPU -> PASS
       `-> compiler-emitted C11  -> static x86_64 ELF -> host -> PASS
  -> digest-bound source-to-target aggregate -> PASS
```

## Bound Evidence

The aggregate validates and binds two already accepted child reports:

- `tests/golden/frontend/oci_source_ingestion_research_proof_report.json`;
- `tests/golden/proofs/bounded_compiler_target_equivalence_proof.json`.

The frontend report proves that one fixed `matmul_elementwise` source buffer is
handled as data by the explicit OCI research worker. It records a malicious
negative case, no source execution, no network, no repository mount, a
read-only root filesystem, non-root execution, dropped capabilities,
no-new-privileges, seccomp, and bounded resources.

The target report proves that the resulting Source Intent digest is also the
input to exactly two AOT compiler targets: CUDA/SASS `sm_86` on a physical GPU
and static C11 `x86_64` in a device-free container. Both target observations
pass separately implemented reference checks.

The common Source Intent digest is:

```text
sha256:79f0fbd3fad9baf3a77df0eea5a1250234c24cdb7d5d6dd703e595816550daaa
```

## Validation

Emit and validate the metadata-only aggregate:

```bash
python3 examples/bounded_source_to_target_execution_proof.py
```

The validator rejects:

- non-canonical or duplicate-key JSON;
- symlinked, oversized, non-object, or changing child reports;
- OCI request, rejection-case, worker, Compose, dependency, vertical-proof,
  or Source Intent provenance drift;
- any mismatch between frontend and target Source Intent;
- any mismatch in operation families;
- target-count, target-identity, execution-model, or child-report drift;
- claim promotion even if the attacker recomputes a report digest;
- source text, generated source, values, commands, host paths, or hardware
  identifiers in public evidence.

The schema is
`schemas/bounded_source_to_target_execution_proof.v0.schema.json`; the accepted
golden is
`tests/golden/proofs/bounded_source_to_target_execution_proof.json`.

## Interpretation

A PASS closes one bounded vertical feasibility path from realistic source form
to executed target artifacts. It strengthens the claim that frontend syntax,
hardware-neutral intent, and target-specific facts can remain separate while
preserving terminal semantics.

It is not a live monolithic pipeline run. It composes separately accepted
frontend and target observations by exact digest. The source case, parser,
emitters, reports, and observations are maintained by the same project owner.

It does not prove arbitrary Triton support, a general parser, default or
production source ingestion, arbitrary-program portability, another ISA,
cross-vendor accelerator execution, general native backends, native
performance, production runtime admission, universal hardware support, vendor
replacement, or independent reproduction. Existing source, native, device,
plugin, generated-artifact, and performance gates remain closed.
