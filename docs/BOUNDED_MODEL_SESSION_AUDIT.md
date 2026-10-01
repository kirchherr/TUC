# Bounded Model Session Audit

The Bounded Model Session Audit makes the retained RFC 0334 execution receipt
reviewable without importing TUC or NumPy and without repeating native
execution. It is a reduced-dependency reimplementation of the fixed evidence
contract, not a second runtime.

Run it with Python 3.11 or newer:

```text
python -I integration/bounded_cpu_model_session_audit/audit_receipt.py \
  docs/evidence/bounded-model-session-36570752112.json
```

The deterministic report must match
`tests/golden/bounded_model_session_audit/report.json`.

## What It Reconstructs

The auditor checks the original 8,508 receipt bytes and their SHA-256 identity,
the observed source commit, wheel and installed consumer identities, four
session summaries, all nine named rejection controls and the result retained
before the terminal numeric failure.

Using only `hashlib`, `json`, `math` and `struct`, it independently:

- rebuilds the canonical identity input for all three fixed models;
- recomputes the three model digests;
- reconstructs the exact binary32 request payload ordering;
- recomputes all 21 request digests;
- evaluates the Linear, changed-parameter and classifier equations with
  explicit binary32 rounding; and
- checks 38 bit-exact and four tolerance-based scalar results.

Program digests stay bound to the observed receipt. Rebuilding generated C11
source is deliberately outside this reduced-dependency contract.

## Security Boundary

The script accepts one regular JSON file no larger than 16 KiB. It rejects
symbolic links, duplicate keys, non-finite JSON numbers, structural drift,
unexpected identities, oversized input and numerical mismatch with one fixed,
source-free diagnostic. It performs no filesystem writes and has no network,
subprocess, package import, plugin, device, generated-code or native execution
surface.

## Claim Boundary

A PASS means the fixed retained receipt is internally consistent with an
independent standard-library implementation of its public identity and
numerical contract. It does not establish independent organizational
reproduction, arbitrary model correctness, resident weights, general runtime
admission or native performance.

Decision: [RFC 0335](../rfcs/0335-bounded-model-session-audit.md).
