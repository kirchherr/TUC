# Backend Author Evidence Gate

Backend Author Evidence Gate v0 is the CI-facing gate for external backend
author onboarding evidence.

It composes:

- Manifest Claim Review
- Backend Author Readiness

Both must pass before the gate emits `PASS`.

## Contract

- Example: `examples/backend_author_evidence_gate.py`
- Golden:
  `tests/golden/backend_author_readiness/backend_author_evidence_gate.txt`
- Tests: `tests/test_backend_author_evidence_gate.py`
- CI: `.github/workflows/ci.yml`

## Security Boundary

The gate is a pure evidence check. It does not scan directories, discover
plugins, import backend modules, load dynamic libraries, spawn subprocesses
outside the Python example process, access devices, touch the network, execute
generated artifacts, run JIT code, or authorize runtime execution.

The CI workflow keeps repository permissions read-only. The gate does not need
write permissions, secrets, deploy keys, publishing tokens, or artifact upload.

## Output

The gate renders deterministic text:

```text
backend_author.evidence_gate @backend_author_evidence_gate_v0 {
  manifest_claim_review = "passed"
  backend_author_readiness = "ready"
  status = "PASS"
}
```

Counts and blocked execution surfaces are included so CI logs show which
evidence set was evaluated.
