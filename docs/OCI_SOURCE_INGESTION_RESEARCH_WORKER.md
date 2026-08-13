# OCI Source Ingestion Research Worker

The OCI Source Ingestion Research Worker is the kernel-isolated successor to
the local process worker. It runs the same narrow, execution-free parser in a
dedicated container and binds the returned Source Intent digest to the existing
no-fallback Systolic/Vector package proof.

```text
bounded module source
  -> fixed OCI worker
  -> kernel and mount invariant checks
  -> source_intent.v0 plain data
  -> strict host validation
  -> existing external package vertical proof
  -> reference correctness + backend equivalence
```

## Enforced Runtime Controls

The `source-ingestion-worker` Compose service has:

- `network_mode: none` and zero observed network routes;
- a read-only root filesystem and no repository or host bind mount;
- all Linux capabilities dropped;
- `no-new-privileges:true`;
- Docker's seccomp filter (`Seccomp=2`);
- a fixed non-root UID/GID;
- one CPU, 1 GiB memory, and 32 PID limits;
- a 16 MiB `noexec,nosuid,nodev` temporary filesystem;
- a fixed Python `-I` entry point and no source-controlled command surface.

The worker reads `/proc` and cgroup v2 state before parsing. It rejects the run
if the observed controls differ from the accepted contract. The host validates
the exact Compose service, bounds stdout/stderr and wall time, validates the
plain-data response, and checks that its Source Intent digest equals the digest
already proven through trusted package execution.

The proof also sends a bounded negative payload containing file-write and
network-call attempts. The worker rejects it with a fixed source-free reason
code; neither payload nor diagnostics enter public evidence.

## Supply Chain Boundary

The image uses a digest-pinned `python:3.12-slim-bookworm` base, a digest-pinned
Dockerfile frontend, and a hash-locked NumPy wheel for `linux/amd64`. The Docker
build context allowlists only `docker/`, `requirements/`, and `src/`; local
documents, Git metadata, caches, credentials, and unrelated files are excluded.

The image is currently built locally and is not published with release
provenance. Therefore this proof does not claim a production sandbox or
production source-ingestion admission.

## Run

```bash
docker compose build source-ingestion-worker
python examples/oci_source_ingestion_research_proof.py
```

Set `TUC_VERIFY_OCI_GOLDEN=1` to require exact golden replay.

## Contract

- Worker image: `docker/source-worker/Dockerfile`
- Runtime service: `docker-compose.yml`
- Hash lock: `requirements/source-worker.txt`
- Worker: `src/tuc/frontend/_isolated_source_ingestion_worker.py`
- Proof: `examples/oci_source_ingestion_research_proof.py`
- Schema: `schemas/oci_source_ingestion_research_proof_report.v0.schema.json`
- Golden: `tests/golden/frontend/oci_source_ingestion_research_proof_report.json`
- Tests: `tests/test_oci_source_ingestion_research_proof.py`
- RFC: `rfcs/0289-oci-source-ingestion-research-worker.md`
