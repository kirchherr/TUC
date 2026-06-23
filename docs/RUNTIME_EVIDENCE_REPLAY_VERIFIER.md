# Runtime Evidence Replay Verifier

Runtime Evidence Replay Verifier v0 is a deterministic, metadata-only verifier
over serialized Runtime Execution Evidence Bundle and Runtime Execution Output
Closure reports.

It answers one narrow question:

```text
Can a reviewer replay the digest bindings between Bundle, Receipt, Output
Contract, Public Output Bundle, and Output Closure without re-running source,
JIT, plugins, devices, or backend artifacts?
```

## Contract

- Report schema: `schemas/runtime_evidence_replay_verifier_report.v0.schema.json`
- Report schema version: `tuc.runtime_evidence_replay_verifier_report.v0`
- Replay contract: `runtime_evidence_replay_verifier.review.v0`
- Replay mode: `metadata_digest_replay_only`
- Input policy: `serialized_json_reports_only`
- Re-execution policy: `runtime_reexecution_not_required`
- Raw value policy: `omitted_by_policy`
- Artifact status: `review_verification`

## Checked Evidence

The verifier accepts serialized JSON text for:

- Runtime Execution Evidence Bundle
- Runtime Execution Output Closure

It checks:

- graph-name agreement;
- Evidence Bundle metadata digest replay;
- Execution Receipt metadata digest replay;
- Output Closure metadata digest replay;
- Output Closure binding to Evidence Bundle;
- Output Closure binding to Execution Receipt;
- Output Closure binding to Runtime Output Contract;
- Output Closure binding to Runtime Public Output Bundle.

## Evidence

Run:

```bash
python examples/runtime_evidence_replay_verifier.py
```

Golden evidence:

```text
tests/golden/runtime_evidence_replay_verifier/proof_of_execution.json
```

## Security Boundary

The verifier treats serialized runtime evidence as untrusted input. It applies
byte limits, parses JSON into data, checks expected contracts, rejects known
source/raw-value fragments, and recomputes metadata digests from bounded report
fields.

It does not parse Python or Triton source, import backend modules, discover
plugins, access devices, spawn subprocesses, run JIT code, load dynamic
libraries, touch the network, execute generated artifacts, or read host paths
from evidence.

## Review Meaning

A passing Runtime Evidence Replay Verifier proves that already-produced runtime
evidence can be independently replay-checked as serialized data. This makes the
proof easier to review outside the original execution context.

It is not a native performance claim, cryptographic attestation, hardware
endorsement, tensor-content hash, source parser completeness claim, or proof
that an arbitrary external artifact is safe to execute.
