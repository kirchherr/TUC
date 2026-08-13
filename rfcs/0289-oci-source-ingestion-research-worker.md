# RFC 0289: OCI Source Ingestion Research Worker

- Status: Accepted
- Date: 2026-08-12
- Area: Secure frontend research

## Summary

Move the bounded Source-to-Intent research slice from process-only containment
into a dedicated hardened OCI worker and bind its output to the existing
no-fallback external package proof.

## Decision

Add a `source-ingestion-worker` service with a digest-pinned minimal Python
image, hash-locked NumPy wheel, fixed non-root entry point, no network, no
volumes, read-only root filesystem, all capabilities dropped,
`no-new-privileges`, seccomp, bounded CPU/memory/PIDs, and a constrained tmpfs.

The worker must observe and validate its own `/proc`, mount, route, and cgroup
facts before parsing. The host proof must independently validate the rendered
Compose contract, bound worker time and output, strictly validate returned
plain data, and require the Source Intent digest already carried through
Systolic/Vector trusted execution with zero fallback, reference correctness,
and backend equivalence.

## Security Boundary

Attacker-controlled source is present only in a bounded stdin JSON request. It
cannot select the image, service, command, entry point, environment, mount,
network, device, plugin, backend, or output path. It is parsed as data and is
never imported, evaluated, JIT-compiled, or executed.

The public report omits source, Source Intent payloads, tensor values, commands,
host paths, runtime handles, and container identifiers.

## Non-Claims

This RFC does not admit general Triton parsing, production source ingestion,
native backend execution, native performance parity, or a production sandbox.
The worker image has no published release provenance or independent security
review yet. Those remain separate admission requirements.

## Acceptance Criteria

- Kernel network isolation and filesystem namespace isolation are observed.
- RootFS is read-only and no repository bind mount exists.
- Seccomp, no-new-privileges, zero capabilities, non-root identity, and cgroup
  limits match the fixed contract.
- Base image, Dockerfile frontend, and runtime wheel are digest/hash pinned.
- Host-side request, output, diagnostics, and wall-clock budgets fail closed.
- A bounded file/network execution probe is rejected source-free.
- Source Intent matches the canonical expected plain data and the existing
  vertical proof digest.
- Public schema and golden remain metadata-only and source-free.
- Dedicated CI rebuilds and replays the OCI proof without write permissions.

## Contract

- Documentation: `docs/OCI_SOURCE_INGESTION_RESEARCH_WORKER.md`
- Dockerfile: `docker/source-worker/Dockerfile`
- Compose: `docker-compose.yml`
- Requirements: `requirements/source-worker.txt`
- Worker: `src/tuc/frontend/_isolated_source_ingestion_worker.py`
- Proof: `examples/oci_source_ingestion_research_proof.py`
- Schema: `schemas/oci_source_ingestion_research_proof_report.v0.schema.json`
- Golden: `tests/golden/frontend/oci_source_ingestion_research_proof_report.json`
- Tests: `tests/test_oci_source_ingestion_research_proof.py`
