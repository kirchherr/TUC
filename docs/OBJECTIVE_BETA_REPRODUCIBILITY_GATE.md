# Objective Beta Reproducibility Gate

Objective Beta Reproducibility Gate v0 independently replays the digest links
declared by the Objective Beta Reproducibility Capsule. Replay means reading
fixed, versioned JSON artifacts and recomputing SHA-256 digests. It never means
re-running source, compilation, runtime execution, backend code, or hardware.

## Gate Contract

The gate fails closed unless all of these checks pass:

- the serialized capsule satisfies its exact v0 contract;
- the artifact set exactly matches the nine-entry internal allowlist;
- every artifact is source-free JSON;
- every artifact byte digest matches the capsule entry;
- the Beta claim digest matches the capsule and Beta gate;
- all seven direct claim evidence links match their artifacts in fixed order;
- the claim metadata digest is preserved;
- external approval remains required;
- source ingestion, native performance, and vendor replacement remain false.

The report publishes only IDs, counts, digests, boolean verification results,
blocked claims, and forbidden execution-surface names. It publishes no paths or
artifact payloads.

## Forbidden Execution Surfaces

The replay contract forbids source, compiler, runtime, backend, plugin,
subprocess, network, device, and generated-artifact execution. The verifier
uses only Python standard-library JSON parsing, fixed file reads, and SHA-256.

## Run

```bash
python examples/objective_beta_reproducibility_gate.py
```

A passing report contains:

```text
gate_status: PASS
gate_passed: true
verified_artifact_count: 9
claim_link_verified: true
evidence_links_verified: true
source_ingestion_admitted: false
```

## Artifacts

- Schema: `schemas/objective_beta_reproducibility_gate_report.v0.schema.json`
- Entrypoint: `examples/objective_beta_reproducibility_gate.py`
- Golden: `tests/golden/proofs/objective_beta_reproducibility_gate.json`
- Capsule: `docs/OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE.md`
- RFC: `rfcs/0281-objective-beta-reproducibility-capsule.md`

## CI Meaning

The existing read-only CI `pytest -q` step executes the capsule and replay
contract, golden, example, and tamper tests. Any silent evidence rewrite, claim
drift, allowlist growth, reordered dependency, or boundary opening fails the
build without changing the digest-bound workflow itself.
