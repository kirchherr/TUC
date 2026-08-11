# RFC 0288: Isolated Source Ingestion Research Worker

- Status: Accepted
- Date: 2026-08-11
- Area: Secure frontend research

## Summary

Move the explicit, bounded Source-to-Intent research parser into one fixed
Linux worker process and bind its validated output to the existing no-fallback
backend package portfolio proof. Keep all production source-ingestion admission
closed.

## Decision

Add `src/tuc/frontend/isolated_source_ingestion.py` as the parent API and
`src/tuc/frontend/_isolated_source_ingestion_worker.py` as the only executable
worker entry point. The parent controls the command, environment, working
directory, timeout, request size, response size, and response validation. The
worker applies CPU, address-space, file-size, open-file, and core-dump resource
limits before loading the parser.

The worker may return Source Intent only through a versioned bounded JSON
protocol. The parent rebuilds that Source Intent through the canonical strict
intake and independently verifies request, module, Source Intent, and ingress
report bindings.

The proof continues the accepted module through Source Intent metadata,
HAC-IR, two data-only external backend packages, trusted Systolic and Vector
simulators, public output closure, reference correctness, and backend
equivalence with zero fallback assignments.

## Security Boundary

The source cannot choose a process, path, argument, environment variable,
import, plugin, backend, device, generated artifact, runtime handle, or public
diagnostic text. Public evidence contains digests and fixed metadata only.

This RFC does not claim filesystem namespace isolation, kernel network
isolation, native-code containment, native backend execution, native
performance parity, a general Triton parser, production source ingestion, or a
production sandbox. A later production proposal must add OS-level namespaces,
syscall filtering, and independent security review before changing those
claims.

## Acceptance Criteria

- The worker command and path are fixed by trusted TUC code.
- Linux resource limits are applied before parser imports.
- Requests and responses are byte-bounded and digest-bound.
- Parent-side Source Intent reconstruction fails closed.
- Malicious source is rejected without execution or source leakage.
- Public proof evidence is schema-closed and omits source and tensor values.
- Reference correctness and backend equivalence pass across the two-package
  portfolio.
- Production source-ingestion and sandbox claims remain false.

## Contract

- Documentation: `docs/ISOLATED_SOURCE_INGESTION_RESEARCH_WORKER.md`
- Parent API: `src/tuc/frontend/isolated_source_ingestion.py`
- Worker: `src/tuc/frontend/_isolated_source_ingestion_worker.py`
- Proof: `examples/isolated_source_ingestion_research_proof.py`
- Schema: `schemas/isolated_source_ingestion_research_proof_report.v0.schema.json`
- Golden: `tests/golden/frontend/isolated_source_ingestion_research_proof_report.json`
- Tests: `tests/test_isolated_source_ingestion_research_proof.py`
