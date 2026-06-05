# Compiler Threat Model

## Scope

This threat model covers the TUC compiler pipeline, backend capability model,
runtime partitioning, simulator backends, future plugins, and generated
artifacts.

## Security Assumptions

- Source code and IR can be malicious.
- Backend manifests can be malicious.
- CI inputs can be malicious.
- A backend may be buggy, compromised, or overly broad in its capability claims.
- A user may compile untrusted kernels or model graphs.

## Assets

- Developer machines.
- CI runners.
- Repository credentials and deploy keys.
- Compiler process integrity.
- Generated artifacts.
- Backend device access.
- Build caches.
- Model metadata and potentially sensitive tensor information.

## Threats And Controls

| Threat | Example | Required Control |
| --- | --- | --- |
| Parser crash or memory corruption | Malformed IR triggers native bug. | Schema validation, fuzzing, ASan/UBSan for native code. |
| Resource exhaustion | Huge tensor dimensions or graph explosion. | Node, rank, dimension, metadata, pass, and time budgets. |
| Arbitrary code execution | Plugin discovery imports attacker code. | Declarative manifests; no code execution during validation. |
| Path traversal | Artifact path escapes cache directory. | Canonicalize and constrain output roots. |
| Wrong-code generation | Unsafe rewrite changes semantics. | Pass invariants, golden tests, explicit error budgets. |
| Confused backend selection | Backend claims support it does not safely provide. | Capability schema, validation, conformance tests. |
| Secret leakage | Diagnostics print tokens or host internals. | Scrub diagnostics; avoid unnecessary environment/path dumps. |
| CI compromise | Workflow runs untrusted PR with write token. | Read-only default permissions; avoid privileged PR workflows. |

## Immediate Security Backlog

1. Add explicit validation APIs for tensor and graph limits.
2. Add malformed-input tests for graph metadata.
3. Add CI `permissions: contents: read`.
4. Add security checklist to PR template.
5. Add CodeQL once the codebase grows beyond the current Python prototype.
6. Add fuzzing plan before serialized IR or native parsing lands.
