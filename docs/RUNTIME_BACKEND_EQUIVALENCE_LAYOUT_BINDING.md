# Runtime Backend Equivalence Layout Binding

Runtime Backend Equivalence Layout Binding v0 is a metadata-only review artifact
for binding the mixed Runtime Backend Equivalence proof slice to the verified
Runtime Layout Conversion Trace Replay Verifier report.

It answers one narrow question:

```text
Does the mixed backend-equivalence proof also carry verified layout-transition
evidence for the same graph and raw-value policy?
```

## Contract

- Report schema:
  `schemas/runtime_backend_equivalence_layout_binding_report.v0.schema.json`
- Report schema version:
  `tuc.runtime_backend_equivalence_layout_binding_report.v0`
- Binding contract:
  `runtime_backend_equivalence_layout_binding.data_only.v0`
- Binding mode: `metadata_digest_binding_only`
- Input policy: `serialized_json_reports_only`
- Reexecution policy: `runtime_reexecution_not_required`
- Raw value policy: `omitted_by_policy`

## Evidence

The canonical example is:

```bash
python examples/runtime_backend_equivalence_layout_binding.py
```

Its deterministic golden report is:

```text
tests/golden/runtime_backend_equivalence_layout_binding/current_report.json
```

## Checks

The report binds:

- Runtime Backend Equivalence contract and pass status
- Runtime Layout Conversion Trace Replay Verifier contract and pass status
- graph name equality
- raw-value policy equality
- mixed candidate backend diversity
- expected trace replay check count
- backend-equivalence report digest
- layout-trace-replay report digest

## Security Boundary

The report accepts only serialized JSON reports. It does not execute runtime
graphs, discover plugins, access devices, materialize layout converters, run
JIT code, spawn subprocesses, or serialize raw tensor values.

It is not a performance claim and not proof of native layout conversion. It is
review evidence that the current mixed backend-equivalence proof is bound to
the layout-conversion evidence chain.
