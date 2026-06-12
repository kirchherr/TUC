# Runtime Evidence Gate

Runtime Evidence Gate v0 is the CI-facing check that combines the current
runtime evidence inventory, trusted executor conformance, Runtime Tensor Store
Evidence, Runtime Backend Equivalence evidence, Runtime Input Manifest
evidence, Runtime Output Manifest evidence, Runtime Output Contract evidence,
Runtime Public Output Bundle evidence, Runtime Reference Correctness evidence,
Runtime Execution Receipt evidence, Runtime Execution Evidence Bundle evidence,
plus Source Intent Runtime Returns evidence for the frontend return boundary.
Source Intent Runtime Returns must also be bound to the curated
Runtime Evidence Matrix graph that inventories the same frontend-originated
fixture.

It runs:

- `build_current_runtime_evidence_matrix_report()`
- `run_runtime_executor_conformance()`
- `build_backend_equivalence_report()`
- `build_vector_backend_equivalence_report()`
- `build_mixed_backend_equivalence_report()`
- `build_tensor_store_evidence_report()`
- `build_input_manifest_report()`
- `build_output_manifest_report()`
- `build_output_contract_report()`
- `build_public_output_bundle()`
- `build_reference_correctness_report()`
- `build_execution_receipt_report()`
- `build_runtime_execution_evidence_bundle_report()`
- `examples/source_intent_runtime_returns.py`
- `examples/runtime_evidence_gate.py`

The gate passes only when:

- the Runtime Evidence Matrix is complete across accepted graph fixtures
- the Runtime Evidence Matrix includes the three backend-equivalence graph
  entries with scoped `backend_equivalence` requirements
- Runtime Executor Conformance passes for the fixed trusted executor registry
- Runtime Backend Equivalence passes for the `reference_cpu` baseline run and
  the `systolic_sim` candidate run
- Runtime Backend Equivalence binding passes, proving the checked report is the
  expected `reference-cpu,reference-cpu` versus `systolic-sim,reference-cpu`
  placement comparison with raw values omitted
- Runtime Backend Equivalence matrix coverage passes, proving the checked
  report is inventoried by the Runtime Evidence Matrix as scoped
  `backend_equivalence` evidence
- Runtime Vector Backend Equivalence passes for the `reference_cpu` baseline
  run and the `vector_sim` candidate run
- Runtime Vector Backend Equivalence binding passes, proving the checked report
  is the expected `reference-cpu,reference-cpu,reference-cpu` versus
  `vector-sim,vector-sim,vector-sim` placement comparison with raw values
  omitted
- Runtime Vector Backend Equivalence matrix coverage passes, proving the
  checked report is inventoried by the Runtime Evidence Matrix as scoped
  `backend_equivalence` evidence
- Runtime Mixed Backend Equivalence passes for the `reference_cpu` baseline run
  and the `mixed_accelerators` candidate run
- Runtime Mixed Backend Equivalence binding passes, proving the checked report
  is the expected `reference-cpu,reference-cpu,reference-cpu,reference-cpu`
  versus `systolic-sim,vector-sim,vector-sim,vector-sim` placement comparison
  with raw values omitted
- Runtime Mixed Backend Equivalence matrix coverage passes, proving the checked
  report is inventoried by the Runtime Evidence Matrix as scoped
  `backend_equivalence` evidence
- Runtime Tensor Store Evidence passes for the current proof-of-execution
  record boundary
- Runtime Input Manifest passes for accepted graph external inputs
- Runtime Output Manifest passes for terminal proof-of-execution outputs
- Runtime Output Contract passes for explicit public output aliases on the
  multi-output runtime fixture
- Runtime Public Output Bundle resolves those aliases to read-only runtime
  values without serializing tensor values into review evidence
- Runtime Reference Correctness passes for terminal proof-of-execution outputs
  against independent reference tensors
- Runtime Execution Receipt passes, proving runtime evidence reports link to
  the same trusted runtime execution by metadata digest and graph name
- Runtime Execution Receipt binding passes, proving receipt links match the
  specific evidence reports evaluated by this gate invocation
- Runtime Execution Evidence Bundle passes, proving the receipt and evidence
  reports form one coherent metadata-only review package
- Runtime Execution Evidence Bundle binding passes, proving embedded report
  metadata matches the specific evidence reports evaluated by this gate
  invocation
- Source Intent Runtime Returns passes, proving explicit frontend return aliases
  resolve through Runtime Output Contract and Runtime Public Output Bundle
- the Source Intent Runtime Returns report is bound to the
  `source_intent_return_mlp` Runtime Evidence Matrix graph, which must use the
  `source_intent_metadata` source boundary and list both
  `source_intent_return_semantics` and `source_intent_runtime_returns`
  artifact kinds

Runtime Input Manifest schema:

```text
schemas/runtime_input_manifest_report.v0.schema.json
```

Runtime Output Manifest schema:

```text
schemas/runtime_output_manifest_report.v0.schema.json
```

Runtime Output Contract schema:

```text
schemas/runtime_output_contract_report.v0.schema.json
```

Runtime Public Output Bundle schema:

```text
schemas/runtime_public_output_bundle_report.v0.schema.json
```

Runtime Reference Correctness schema:

```text
schemas/runtime_reference_correctness_report.v0.schema.json
```

Runtime Execution Receipt schema:

```text
schemas/runtime_execution_receipt_report.v0.schema.json
```

Runtime Execution Evidence Bundle schema:

```text
schemas/runtime_execution_evidence_bundle_report.v0.schema.json
```

Runtime Backend Equivalence schema:

```text
schemas/runtime_backend_equivalence_report.v0.schema.json
```

Source Intent Runtime Returns schema:

```text
schemas/source_intent_runtime_returns_report.v0.schema.json
```

Golden output:

```text
tests/golden/proofs/runtime_evidence_gate.txt
```

CI entry:

```text
.github/workflows/ci.yml
```

## Security Boundary

The gate does not scan the repository, discover backends, import plugins,
access devices, load dynamic libraries, spawn subprocesses, run JIT code, touch
the network, execute generated artifacts, capture command lines, load raw
benchmark output, or authorize external executable backends.

It composes bounded in-repository checks:

- data-only evidence identifiers from Runtime Evidence Matrix v0
- fixed in-memory operation fixtures from Runtime Executor Conformance v0
- data-only Runtime Backend Equivalence metadata comparing the expected
  `reference_cpu` and `systolic_sim` trusted execution placements with raw
  tensor values omitted by policy
- a bounded Runtime Backend Equivalence binding check that verifies graph ID,
  run IDs, planned backend sequences, matched comparison status, and raw-value
  policy
- a bounded Runtime Backend Equivalence matrix lookup that verifies graph
  family, source boundary, required artifact kinds, completeness, and
  `backend_equivalence` artifact coverage
- data-only Runtime Vector Backend Equivalence metadata comparing the expected
  `reference_cpu` and `vector_sim` trusted execution placements with raw tensor
  values omitted by policy
- a bounded Runtime Vector Backend Equivalence binding check that verifies graph
  ID, run IDs, planned backend sequences, matched comparison status, and
  raw-value policy
- a bounded Runtime Vector Backend Equivalence matrix lookup that verifies graph
  family, source boundary, required artifact kinds, completeness, and
  `backend_equivalence` artifact coverage
- data-only Runtime Mixed Backend Equivalence metadata comparing the expected
  `reference_cpu` and `mixed_accelerators` trusted execution placements with
  raw tensor values omitted by policy
- a bounded Runtime Mixed Backend Equivalence binding check that verifies graph
  ID, run IDs, planned backend sequences, matched comparison status, and
  raw-value policy
- a bounded Runtime Mixed Backend Equivalence matrix lookup that verifies graph
  family, source boundary, required artifact kinds, completeness, and
  `backend_equivalence` artifact coverage
- data-only Runtime Tensor Store record metadata with raw tensor values omitted
  by policy
- data-only Runtime Input Manifest metadata for accepted graph external inputs
  with raw tensor values omitted by policy
- data-only Runtime Output Manifest metadata for terminal graph outputs with raw
  tensor values omitted by policy
- data-only Runtime Output Contract metadata for public output aliases with raw
  tensor values omitted by policy
- Runtime Public Output Bundle metadata for read-only public output values with
  raw tensor values omitted by policy
- data-only Runtime Reference Correctness metadata with output and reference
  tensor values omitted by policy
- data-only Runtime Execution Receipt metadata linking runtime evidence digests
  with raw tensor values omitted by policy
- a bounded Runtime Execution Receipt binding check that compares receipt graph
  names, contracts, metadata digests, item counts, pass status, and raw-value
  policy against the reports already checked by the gate
- data-only Runtime Execution Evidence Bundle metadata embedding the runtime
  evidence reports and receipt with raw tensor values omitted by policy
- a bounded Runtime Execution Evidence Bundle binding check that compares
  embedded graph names, contracts, metadata digests, item counts, pass status,
  and raw-value policy against the reports already checked by the gate
- data-only Source Intent Runtime Returns metadata proving frontend public
  returns resolve to runtime public outputs with raw tensor values omitted by
  policy
- a bounded matrix lookup for `source_intent_return_mlp`; the lookup checks only
  graph IDs, source boundary labels, artifact-kind labels, and runtime evidence
  completeness

The output is a small deterministic text report ending in `PASS`.

## Review Meaning

This gate is not a native performance claim. It is a merge-time confidence
check that the accepted proof fixtures still have complete runtime evidence and
that the trusted executor registry still matches its declared support surface.
