# RFC 0304: Bounded Source-To-Target Execution Proof

## Status

Accepted after the closed source-to-target aggregate, schema, golden evidence,
negative provenance tests, and read-only CI validation passed. This RFC does
not admit source ingestion or a native TUC backend.

## Context

RFC 0302 established one exact Source Intent-to-physical-GPU code-generation
path. RFC 0303 bound that same Source Intent to a separately specified static
C11 target. The result still began at Source Intent, leaving the strongest
frontend criticism unanswered inside that proof chain.

TUC already has a separately bounded OCI source-ingestion research worker. It
accepts one fixed Triton-shaped `matmul_elementwise` module as inert data,
rejects a malicious source case, emits a canonical `source_intent.v0` payload,
and keeps production admission closed. Its accepted Source Intent digest is
identical to the digest in RFCs 0302 and 0303.

The next bounded research question is:

> Can those independently executed, previously accepted frontend and target
> procedures be joined into one closed vertical claim without executing source
> text, widening parser syntax, or opening a normal runtime path?

## Decision

Add a metadata-only aggregate that first validates:

1. the accepted OCI Source Ingestion Research Proof report; and
2. the accepted Bounded Compiler Target Equivalence report.

Strengthen the OCI child validator so its Compose contract, Dockerfile,
requirements, canonical worker request, malicious rejection request, expected
Source Intent, vertical proof, and worker implementation digests must match
the current reviewed artifacts rather than merely matching a digest pattern.

The aggregate must then require:

- the canonical fixed source request and Source Intent;
- exact Source Intent digest equality across frontend and target evidence;
- equal Matmul-plus-ReLU operation families;
- exactly two fixed AOT target observations;
- passing reference correctness on both targets;
- equal terminal reference semantics;
- no source execution, runtime code generation, raw source, generated source,
  raw tensor values, commands, host paths, or hardware identifiers in the
  public report.

The existing source worker, parser subset, compiler emitters, normal executor,
native backend registry, and device gates are unchanged.

## Security Boundary

Both child reports are untrusted input. The aggregate uses strict UTF-8 and
JSON decoding, duplicate-key and non-finite-number rejection, byte and
structural limits inherited from the existing decoder, symlink rejection,
before-and-after file checks, exact key closure, canonical SHA-256 digests, and
full child validators before building a claim.

The validator reconstructs the only accepted aggregate from checked-in child
evidence. Recomputing a digest after changing a child provenance field or
promoting a blocked claim is insufficient to pass. Output remains metadata
only.

This RFC adds no subprocess, import discovery, dynamic library, generated-code
execution, device access, network access, writable mount, secret, or new
dependency. CI remains read-only and uses the already pinned actions and
hash-locked dependency set.

## Claim Boundary

A passing report establishes only:

> One fixed Triton-shaped source buffer was treated as inert data by the
> bounded OCI research worker, produced the exact Source Intent already used by
> two same-maintainer compiler targets, and those accepted CUDA/SASS and static
> C11 observations preserved terminal reference semantics.

It does not establish arbitrary source support, a general Triton parser,
default or production source ingestion, arbitrary-program portability,
cross-ISA portability, cross-vendor accelerator execution, general native
backends, native performance parity, production runtime admission, universal
hardware support, vendor replacement, or independent reproduction.

The aggregate is a digest-bound composition of accepted procedures, not a new
single-process execution path. All evidence remains same-maintainer evidence.

## Evidence

- aggregate: `examples/bounded_source_to_target_execution_proof.py`;
- schema:
  `schemas/bounded_source_to_target_execution_proof.v0.schema.json`;
- accepted report:
  `tests/golden/proofs/bounded_source_to_target_execution_proof.json`;
- frontend child:
  `tests/golden/frontend/oci_source_ingestion_research_proof_report.json`;
- target child:
  `tests/golden/proofs/bounded_compiler_target_equivalence_proof.json`;
- tests: `tests/test_bounded_source_to_target_execution_proof.py`;
- procedure: `docs/BOUNDED_SOURCE_TO_TARGET_EXECUTION_PROOF.md`.

## Consequences

TUC now has one inspectable path from realistic source form through canonical
hardware-neutral intent to two materially different executed target artifacts.
This addresses frontend-to-target continuity without pretending that a narrow
research parser is a production frontend.

The next generalization must add genuinely independent evidence, a new source
program with separately reviewed semantics, or another ISA or vendor. Merely
adding syntax aliases or another build of the same targets is insufficient.
