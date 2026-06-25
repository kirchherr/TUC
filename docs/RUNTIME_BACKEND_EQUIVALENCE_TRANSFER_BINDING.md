# Runtime Backend Equivalence Transfer Binding

Runtime Backend Equivalence Transfer Binding v0 is a metadata-only review
artifact for binding the systolic Runtime Backend Equivalence proof slice to
the verified Runtime Transfer Trace Replay Verifier report.

It answers one narrow question:

```text
Does the systolic backend-equivalence proof also carry verified transfer-trace
evidence for the same graph and raw-value policy?
```

## Contract

- Report schema:
  `schemas/runtime_backend_equivalence_transfer_binding_report.v0.schema.json`
- Report schema version:
  `tuc.runtime_backend_equivalence_transfer_binding_report.v0`
- Binding contract:
  `runtime_backend_equivalence_transfer_binding.data_only.v0`
- Binding mode: `metadata_digest_binding_only`
- Input policy: `serialized_json_reports_only`
- Reexecution policy: `runtime_reexecution_not_required`
- Raw value policy: `omitted_by_policy`

## Evidence

The canonical example is:

```bash
python examples/runtime_backend_equivalence_transfer_binding.py
```

Its deterministic golden report is:

```text
tests/golden/runtime_backend_equivalence_transfer_binding/current_report.json
```

## Checks

The report binds:

- Runtime Backend Equivalence contract and pass status
- Runtime Transfer Trace Replay Verifier contract and pass status
- graph name equality
- raw-value policy equality
- candidate backend boundary diversity
- expected transfer replay check count
- backend-equivalence report digest
- transfer-trace-replay report digest

## Security Boundary

The report accepts only serialized JSON reports. It does not execute runtime
graphs, discover plugins, access devices, materialize transfers, run JIT code,
spawn subprocesses, or serialize raw tensor values.

It is not a performance claim and not proof of native device transfer. It is
review evidence that the current systolic backend-equivalence proof is bound to
the transfer evidence chain.