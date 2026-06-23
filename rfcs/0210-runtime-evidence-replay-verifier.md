# RFC 0210: Runtime Evidence Replay Verifier

## Status

Accepted

## Context

Runtime Execution Evidence Bundle and Runtime Execution Output Closure already
show that one trusted runtime execution has coherent metadata-only evidence.
Reviewers still need a compact replay artifact that checks serialized evidence
again without depending on the original execution context.

## Decision

Add Runtime Evidence Replay Verifier v0:

- implementation: `src/tuc/runtime/evidence_replay_verifier.py`
- example: `examples/runtime_evidence_replay_verifier.py`
- schema: `schemas/runtime_evidence_replay_verifier_report.v0.schema.json`
- docs: `docs/RUNTIME_EVIDENCE_REPLAY_VERIFIER.md`
- golden: `tests/golden/runtime_evidence_replay_verifier/proof_of_execution.json`

The verifier accepts serialized JSON reports for Runtime Execution Evidence
Bundle and Runtime Execution Output Closure. It replay-checks graph-name
agreement, bundle metadata digest, execution receipt metadata digest, output
closure metadata digest, and the closure links to Evidence Bundle, Receipt,
Output Contract, and Public Output Bundle.

## Security Boundary

The verifier treats serialized reports as untrusted input. It applies byte
limits, parses JSON into data only, rejects source/raw-value fragments, and
does not execute source, JIT, plugins, backend artifacts, subprocesses,
dynamic libraries, devices, generated code, host paths, or network access.

## Consequences

TUC gains a practical reviewer-facing replay step for existing runtime evidence
without widening the compiler or runtime attack surface. The artifact remains a
metadata-digest verifier; it is not a performance claim, cryptographic
attestation, tensor-content hash, or production parser claim.
