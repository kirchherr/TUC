# Isolated Source Ingestion Research Worker

The isolated Source Ingestion Research Worker is a Linux-only, non-admitting
prototype that moves the narrow Triton-like research parser out of the parent
process and then completes the existing trusted package-portfolio proof.

```text
bounded module source
  -> fixed isolated worker
  -> validated source_intent.v0 plain data
  -> parent-side revalidation
  -> HAC-IR and capability planning
  -> external-systolic + external-vector package projection
  -> trusted simulator execution
  -> reference correctness + backend equivalence
```

Run the complete proof with:

```bash
python examples/isolated_source_ingestion_research_proof.py
```

## Enforced Boundary

The parent uses an absolute fixed worker path, `shell=False`, Python `-I`, a
minimal environment, an empty temporary working directory, closed inherited
file descriptors, a parent wall-clock timeout, and bounded anonymous files for
stdout and stderr. The worker applies Linux `RLIMIT` controls for CPU time,
address space, output file size, open files, and core dumps before importing the
TUC parser.

Requests and responses are bounded JSON. The request is digest-bound. The
parent rejects unknown protocol fields, validates the worker security facts,
recomputes Source Intent and module digests, and reconstructs the returned
`SourceIntentModule` through the strict plain-data intake.

Attacker-controlled source is parsed as data. It is never imported, compiled,
evaluated, executed, passed to a shell, selected as a command, or allowed to
choose a worker path.

## Honest Non-Claims

This process boundary does not provide a filesystem namespace, kernel-enforced
network isolation, a native-code sandbox, production source ingestion, or a
production source sandbox. The worker contains no source-controlled network or
filesystem behavior, but absolute host-path and network denial still require a
future OS sandbox such as namespaces plus syscall filtering.

Therefore:

```text
research_source_to_intent_plain_data = true
direct_source_ingestion = false
production_source_ingestion = false
kernel_network_isolation = false
filesystem_namespace_isolation = false
```

The existing maintainer approval and Source Ingestion Admission Gate remain
unchanged and fail closed.

## Evidence Contract

- Parent API: `src/tuc/frontend/isolated_source_ingestion.py`
- Fixed worker: `src/tuc/frontend/_isolated_source_ingestion_worker.py`
- Proof: `examples/isolated_source_ingestion_research_proof.py`
- Schema: `schemas/isolated_source_ingestion_research_proof_report.v0.schema.json`
- Golden: `tests/golden/frontend/isolated_source_ingestion_research_proof_report.json`
- Tests: `tests/test_isolated_source_ingestion_research_proof.py`
- RFC: `rfcs/0288-isolated-source-ingestion-research-worker.md`
