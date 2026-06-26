# RFC 0231: Objective Alpha Source Ingress Public Entries

- Status: accepted-for-prototype
- Created: 2026-06-26
- Phase: Alpha / Frontend Evidence

## Summary

Expose the existing Source-To-Intent Research Proof Bundle and Source-To-Intent
Research Kernel Ingress Evidence Gate as digest-only entries in the Objective
Alpha Public Proof Bundle.

This RFC does not enable the default source parser, execute Triton source,
execute decorators, import Python modules, discover plugins, access devices,
load dynamic libraries, run JIT code, spawn subprocesses, or claim native
performance parity.

## Motivation

Objective Alpha now has strong runtime and backend-equivalence evidence. The
Master Plan also names realistic Triton-shaped source ingress as a credibility
milestone. Reviewers need to see that the current controlled source-ingress
research path is bound to the public proof entrypoint without turning the public
bundle into a source parser or a raw-source archive.

## Decision

Add two fixed public bundle entries:

- `source_to_intent_research_proof_bundle`, emitted by
  `python examples/source_to_intent_research_proof_bundle.py`;
- `source_to_intent_research_kernel_ingress_evidence_gate`, emitted by
  `python examples/source_to_intent_research_kernel_ingress_evidence_gate.py`.

Both entries are represented only by SHA-256 metadata digests and fixed entry
point metadata. The Objective Alpha Public Proof Bundle Gate also gains explicit
invariants requiring these entries to remain direct public entries.

## Security Boundary

The bundle still runs only trusted in-repository evidence builders. It records
no raw source text, source buffers, tensor values, timing samples, host paths,
device identifiers, backend artifacts, generated code, runtime handles, command
lines, or dynamic execution permission.

The research parser remains explicit-only and blocked as a default compiler
intake path. The Kernel Ingress evidence remains source-free review evidence for
a bounded research slice.

## Consequences

- The public Objective Alpha entrypoint now connects runtime/backend evidence to
  controlled Source-To-Intent and Kernel Ingress research evidence.
- The bundle reaches its current fixed 16-entry cap.
- The bundle and gate emit the fixed entry capacity as review metadata.
- Future additions need a deliberate bundle-capacity decision rather than
  silent public entry growth.
- Broad source parsing, native performance, vendor replacement, arbitrary
  third-party backend execution, device access, and generated-artifact execution
  remain blocked claims.