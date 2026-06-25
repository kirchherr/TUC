# Runtime Evidence Gate

Runtime Evidence Gate v0 is the CI-facing check that combines the current
runtime evidence inventory, trusted executor conformance, Runtime Tensor Store
Evidence, Runtime Backend Equivalence and Backend Equivalence Portfolio
evidence, Runtime Planning Explanation evidence, Runtime Transfer Trace Index
evidence, Runtime HS-IR Plan Alignment evidence, Runtime Layout Conversion
Trace Index evidence, Runtime Input Manifest
evidence, Runtime Output Manifest evidence, Runtime Output Contract evidence,
Runtime Public Output Bundle evidence, Runtime Reference Correctness evidence,
Runtime Execution Receipt evidence, Runtime Execution Evidence Bundle evidence,
Runtime Execution Output Closure evidence, Runtime Memory Planning Gate evidence,
plus Source Intent Runtime Returns evidence for the frontend return boundary.
The CI runtime evidence path also runs `examples/runtime_evidence_replay_verifier.py`
as a companion replay check over serialized Bundle and Output Closure reports,
and `examples/runtime_layout_conversion_trace_replay_verifier.py` as a companion
replay check over serialized Layout Conversion Evidence and Trace Index reports,
and `examples/runtime_backend_equivalence_layout_binding.py` as a companion
binding check over serialized Mixed Backend Equivalence and Layout Trace Replay reports.
Source Intent Runtime Returns must also be bound to the curated
Runtime Evidence Matrix graph that inventories the same frontend-originated
fixture.

It runs:

- `build_current_runtime_evidence_matrix_report()`
- `run_runtime_executor_conformance()`
- `build_backend_equivalence_report()`
- `examples/runtime_planning_explanation.py`
- `examples/runtime_transfer_trace_index.py`
- `examples/runtime_mixed_planning_explanation.py`
- `build_vector_backend_equivalence_report()`
- `build_mixed_backend_equivalence_report()`
- `examples/runtime_hs_ir_plan_alignment.py`
- `examples/runtime_layout_conversion_evidence.py`
- `examples/runtime_layout_conversion_trace_index.py`
- `examples/runtime_layout_conversion_trace_replay_verifier.py`
- `examples/runtime_backend_equivalence_layout_binding.py`
- `examples/runtime_mixed_tensor_store_evidence.py`
- `examples/runtime_layout_conversion_digest_binding.py`
- `examples/runtime_layout_conversion_gate_readiness.py`
- `examples/runtime_layout_conversion_gate_promotion_policy.py`
- `build_runtime_backend_equivalence_portfolio_report()`
- `build_default_runtime_backend_equivalence_portfolio_policy_report()`
- `build_runtime_evidence_gate_matrix_coverage_report()`
- `examples/runtime_memory_planning_gate.py`
- `build_tensor_store_evidence_report()`
- `build_input_manifest_report()`
- `build_output_manifest_report()`
- `build_output_contract_report()`
- `build_public_output_bundle()`
- `build_reference_correctness_report()`
- `build_execution_receipt_report()`
- `build_execution_receipt_evidence_reports()`
- `build_runtime_execution_evidence_bundle_report()`
- `build_runtime_execution_output_closure_report()`
- `examples/source_intent_runtime_returns.py`
- `examples/runtime_evidence_gate.py`

The gate passes only when:

- the Runtime Evidence Matrix is complete across accepted graph fixtures
- the Runtime Evidence Matrix includes the three backend-equivalence graph
  entries, with the systolic entry requiring `runtime_planning_explanation`
  and `runtime_transfer_trace_index`, and the mixed entry requiring
  `runtime_planning_explanation`, `runtime_hs_ir_plan_alignment`,
  `runtime_layout_conversion_evidence`,
  `runtime_layout_conversion_trace_index`,
  `runtime_layout_conversion_trace_replay_verifier`, and
  `runtime_backend_equivalence_layout_binding`, plus exact artifact-ID bindings
- the Runtime Evidence Matrix includes the backend-equivalence portfolio graph
  entry with scoped `backend_equivalence_portfolio` and
  `backend_equivalence_portfolio_policy` requirements and exact artifact-ID
  bindings
- the Runtime Evidence Matrix includes `runtime_hs_ir_plan_alignment` evidence
  on the mixed backend-equivalence graph with exact artifact-ID binding
- Runtime Evidence Gate Matrix Coverage passes, proving the exact
  backend-equivalence, runtime-planning-explanation, transfer trace-index,
  HS-IR alignment, layout-conversion, trace-index, portfolio, and
  memory-planning Matrix graph/artifact bindings are present in one
  deterministic audit report
- Runtime Executor Conformance passes for the fixed trusted executor registry
- Runtime Backend Equivalence passes for the `reference_cpu` baseline run and
  the `systolic_sim` candidate run
- Runtime Backend Equivalence binding passes, proving the checked report is the
  expected `reference-cpu,reference-cpu` versus `systolic-sim,reference-cpu`
  placement comparison with raw values omitted
- Runtime Backend Equivalence matrix coverage passes, proving the checked
  report is inventoried by the Runtime Evidence Matrix as scoped
  `backend_equivalence` evidence with the exact
  `runtime_backend_equivalence_systolic` artifact ID
- Runtime Planning Explanation passes for the same systolic candidate plan
- Runtime Planning Explanation binding passes, proving the checked explanation
  report is the expected `systolic-sim,reference-cpu` backend sequence with
  visible fallback and recorded candidate-score diagnostics
- Runtime Planning Explanation matrix coverage passes, proving the explanation
  report is inventoried by the Runtime Evidence Matrix with the exact
  `runtime_planning_explanation_systolic` artifact ID
- Runtime Transfer Trace Index passes for the same systolic candidate plan
- Runtime Transfer Trace Index binding passes, proving the checked index is
  tied to the same graph, transfer count, planned transfer bytes, backend pair,
  and candidate trace-step count evaluated by this gate invocation
- Runtime Transfer Trace Index matrix coverage passes, proving the index is
  inventoried by the Runtime Evidence Matrix with the exact
  `runtime_transfer_trace_index_systolic` artifact ID
- Runtime Vector Backend Equivalence passes for the `reference_cpu` baseline
  run and the `vector_sim` candidate run
- Runtime Vector Backend Equivalence binding passes, proving the checked report
  is the expected `reference-cpu,reference-cpu,reference-cpu` versus
  `vector-sim,vector-sim,vector-sim` placement comparison with raw values
  omitted
- Runtime Vector Backend Equivalence matrix coverage passes, proving the
  checked report is inventoried by the Runtime Evidence Matrix as scoped
  `backend_equivalence` evidence with the exact
  `runtime_backend_equivalence_vector` artifact ID
- Runtime Mixed Backend Equivalence passes for the `reference_cpu` baseline run
  and the `mixed_accelerators` candidate run
- Runtime Mixed Backend Equivalence binding passes, proving the checked report
  is the expected `reference-cpu,reference-cpu,reference-cpu,reference-cpu`
  versus `systolic-sim,vector-sim,vector-sim,vector-sim` placement comparison
  with raw values omitted
- Runtime Mixed Backend Equivalence matrix coverage passes, proving the checked
  report is inventoried by the Runtime Evidence Matrix as scoped
  `backend_equivalence` evidence with the exact
  `runtime_backend_equivalence_mixed` artifact ID
- Runtime Mixed Planning Explanation passes for the same mixed accelerator
  candidate plan
- Runtime Mixed Planning Explanation binding passes, proving the checked
  explanation report is the expected
  `systolic-sim,vector-sim,vector-sim,vector-sim` backend sequence with no
  fallback, visible layout-conversion movement, and recorded candidate-score
  diagnostics
- Runtime Mixed Planning Explanation matrix coverage passes, proving the
  explanation report is inventoried by the Runtime Evidence Matrix with the
  exact `runtime_planning_explanation_mixed` artifact ID
- Runtime HS-IR Plan Alignment passes for the mixed accelerator proof slice
- Runtime HS-IR Plan Alignment binding passes, proving the checked report is
  the expected `systolic-sim,vector-sim,vector-sim,vector-sim` HS-IR,
  PartitionPlan, and RuntimeExecutionTrace alignment with raw values omitted
- Runtime HS-IR Plan Alignment matrix coverage passes, proving the checked
  report is inventoried by the Runtime Evidence Matrix with the exact
  `runtime_hs_ir_plan_alignment_mixed` artifact ID
- Runtime Layout Conversion Evidence passes for the mixed accelerator proof
  slice
- Runtime Layout Conversion Evidence binding passes, proving conversion count
  and planned bytes agree with Mixed Planning Explanation and HS-IR Plan
  Alignment
- Runtime Layout Conversion Evidence matrix coverage passes, proving the report
  is required by the Runtime Evidence Matrix with the exact
  `runtime_layout_conversion_evidence_mixed` artifact ID
- Runtime Layout Conversion Trace Index passes for the mixed accelerator proof
  slice
- Runtime Layout Conversion Trace Index binding passes, proving the trace index
  is tied to the same graph, partition-plan digest, layout-conversion evidence
  digest, conversion count, and mixed candidate trace-step count evaluated by
  this gate invocation
- Runtime Layout Conversion Trace Index matrix coverage passes, proving the
  report is required by the Runtime Evidence Matrix with the exact
  `runtime_layout_conversion_trace_index_mixed` artifact ID
- Runtime Layout Conversion Trace Replay Verifier passes for the mixed
  accelerator proof slice
- Runtime Layout Conversion Trace Replay Verifier binding passes, proving the
  serialized Layout Conversion Evidence and Trace Index reports replay by
  metadata digest for the same graph and policies evaluated by this gate
- Runtime Layout Conversion Trace Replay Verifier matrix coverage passes,
  proving the report is required by the Runtime Evidence Matrix with the exact
  `runtime_layout_conversion_trace_replay_verifier_mixed` artifact ID
- Runtime Backend Equivalence Layout Binding passes for the mixed accelerator
  proof slice
- Runtime Backend Equivalence Layout Binding binding passes, proving the mixed
  Backend Equivalence report is bound to verified layout trace replay by
  metadata digest, graph name, raw-value policy, and mixed candidate backend
  diversity
- Runtime Backend Equivalence Layout Binding matrix coverage passes, proving
  the report is required by the Runtime Evidence Matrix with the exact
  `runtime_backend_equivalence_layout_binding_mixed` artifact ID
- Runtime Layout Conversion Digest Binding passes, proving the layout-conversion
  metadata digest is bound to HS-IR alignment metadata and Mixed Tensor Store
  metadata
- Runtime Layout Conversion Gate Readiness is ready and Runtime Layout
  Conversion Gate Promotion Policy is accepted with enforcement by Runtime
  Evidence Gate
- Runtime Backend Equivalence Portfolio passes across the systolic, vector, and
  mixed accelerator proof slices
- Runtime Backend Equivalence Portfolio binding passes, proving the aggregate
  portfolio is built from the exact Backend Equivalence reports evaluated by
  this gate invocation
- Runtime Backend Equivalence Portfolio matrix coverage passes, proving the
  portfolio is inventoried by the Runtime Evidence Matrix as scoped
  `backend_equivalence_portfolio` and
  `backend_equivalence_portfolio_policy` evidence with exact portfolio and
  policy artifact IDs
- Runtime Backend Equivalence Portfolio Policy binding passes, proving the
  accepted slice membership and backend sequences match the portfolio report
- Runtime Memory Planning Gate passes, proving Buffer Lifetime, Allocation
  Plan, Memory Budget, Allocation Request Manifest, Allocation Admission, and
  Allocation Receipt evidence agree by metadata digest and keep runtime handles
  omitted
- Runtime Memory Planning matrix coverage passes, proving the memory-planning
  graph is inventoried by Runtime Evidence Matrix with exact artifact IDs
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
- Runtime Execution Output Closure passes, proving the proof-of-execution
  Output Contract and Runtime Public Output Bundle are bound identically by the
  Runtime Execution Receipt and Runtime Execution Evidence Bundle
- Runtime Execution Output Closure binding passes, proving the closure report
  matches the specific receipt and bundle evaluated by this gate invocation
- the CI companion Runtime Evidence Replay Verifier passes, proving serialized
  Bundle and Output Closure evidence can be replay-checked by metadata digest
  without re-running source, JIT, plugins, devices, or backend artifacts
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

Runtime Execution Output Closure schema:

```text
schemas/runtime_execution_output_closure_report.v0.schema.json
```

Runtime Evidence Replay Verifier schema:

```text
schemas/runtime_evidence_replay_verifier_report.v0.schema.json
```

Runtime Layout Conversion Trace Replay Verifier schema:

```text
schemas/runtime_layout_conversion_trace_replay_verifier_report.v0.schema.json
```

Runtime Backend Equivalence Layout Binding schema:

```text
schemas/runtime_backend_equivalence_layout_binding_report.v0.schema.json
```


Runtime Backend Equivalence schema:

```text
schemas/runtime_backend_equivalence_report.v0.schema.json
```

Runtime Backend Equivalence Portfolio schema:

```text
schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json
```

Runtime Backend Equivalence Portfolio Policy schema:

```text
schemas/runtime_backend_equivalence_portfolio_policy_report.v0.schema.json
```

Runtime HS-IR Plan Alignment schema:

```text
schemas/runtime_hs_ir_plan_alignment_report.v0.schema.json
```

Runtime Planning Explanation schema:

```text
schemas/runtime_planning_explanation_report.v0.schema.json
```

Runtime Transfer Trace Index schema:

```text
schemas/runtime_transfer_trace_index_report.v0.schema.json
```

Runtime Layout Conversion Trace Index schema:

```text
schemas/runtime_layout_conversion_trace_index_report.v0.schema.json
```

Runtime Evidence Gate Matrix Coverage schema:

```text
schemas/runtime_evidence_gate_matrix_coverage_report.v0.schema.json
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
  exact `backend_equivalence` artifact coverage
- data-only Runtime Planning Explanation metadata explaining the accepted
  systolic and mixed candidate plans with backend sequence, fallback or
  no-fallback placement, candidate-score visibility, and movement bytes
- data-only Runtime Transfer Trace Index metadata binding the systolic
  backend-equivalence planned transfer edge to producer and consumer trace-step
  indexes without materializing a transfer step
- bounded Runtime Transfer Trace Index checks that compare graph name, transfer
  count, planned transfer bytes, producer/consumer backend pair, trace-step
  count, raw-value policy, execution policy, and Matrix artifact binding
- bounded Runtime Planning Explanation binding checks that compare graph ID,
  candidate backend sequence, operation count, fallback/no-fallback visibility,
  candidate-score visibility, and movement visibility against Backend
  Equivalence reports already checked by the gate
- bounded Runtime Planning Explanation matrix lookups that verify graph
  family, source boundary, required artifact kinds, completeness, and exact
  `runtime_planning_explanation` artifact coverage
- bounded Runtime Transfer Trace Index matrix lookups that verify graph family,
  source boundary, required artifact kinds, completeness, and exact
  `runtime_transfer_trace_index` artifact coverage
- data-only Runtime Vector Backend Equivalence metadata comparing the expected
  `reference_cpu` and `vector_sim` trusted execution placements with raw tensor
  values omitted by policy
- a bounded Runtime Vector Backend Equivalence binding check that verifies graph
  ID, run IDs, planned backend sequences, matched comparison status, and
  raw-value policy
- a bounded Runtime Vector Backend Equivalence matrix lookup that verifies graph
  family, source boundary, required artifact kinds, completeness, and
  exact `backend_equivalence` artifact coverage
- data-only Runtime Mixed Backend Equivalence metadata comparing the expected
  `reference_cpu` and `mixed_accelerators` trusted execution placements with
  raw tensor values omitted by policy
- a bounded Runtime Mixed Backend Equivalence binding check that verifies graph
  ID, run IDs, planned backend sequences, matched comparison status, and
  raw-value policy
- a bounded Runtime Mixed Backend Equivalence matrix lookup that verifies graph
  family, source boundary, required artifact kinds, completeness, and
  exact `backend_equivalence` artifact coverage
- data-only Runtime HS-IR Plan Alignment metadata binding HS-IR backend/layout
  facts to the accepted mixed `PartitionPlan` and observed trusted runtime
  trace with raw tensor values omitted by policy
- a bounded Runtime HS-IR Plan Alignment binding check that compares graph
  names, backend sequences, step count, pass status, and raw-value policy
  against the mixed Backend Equivalence report already checked by the gate
- a bounded Runtime HS-IR Plan Alignment matrix lookup that verifies graph
  family, source boundary, required artifact kinds, completeness, and exact
  `runtime_hs_ir_plan_alignment` artifact coverage
- data-only Runtime Layout Conversion Trace Index metadata binding planned
  conversion evidence to producer and consumer trace-step indexes without
  materializing a converter step
- bounded Runtime Layout Conversion Trace Index checks that compare graph name,
  conversion count, partition-plan digest, source evidence digest, trace-step
  count, raw-value policy, execution policy, and Matrix artifact binding
- data-only Runtime Backend Equivalence Portfolio metadata aggregating the
  systolic, vector, and mixed accelerator equivalence slices with raw tensor
  values omitted by policy
- a bounded Runtime Backend Equivalence Portfolio binding check that compares
  slice IDs, graph names, run IDs, backend sequences, comparison counts,
  comparison metadata digests, pass status, candidate backend families, and
  raw-value policy against the reports already checked by the gate
- a bounded Runtime Backend Equivalence Portfolio matrix lookup that verifies
  graph family, source boundary, required artifact kinds, completeness, and
  exact `backend_equivalence_portfolio` and
  `backend_equivalence_portfolio_policy` artifact coverage
- data-only Runtime Backend Equivalence Portfolio Policy metadata declaring the
  accepted slice IDs, graph names, run IDs, backend sequences, minimum
  comparison counts, and covered candidate backend families
- a bounded Runtime Backend Equivalence Portfolio Policy binding check that
  verifies the portfolio report matches that accepted membership policy
- data-only Runtime Evidence Gate Matrix Coverage metadata auditing the exact
  Matrix graph/artifact bindings accepted by the gate
- a bounded Runtime Evidence Gate Matrix Coverage check that fails closed if a
  gate-required graph, source boundary, required artifact kind, or concrete
  artifact ID drifts
- data-only Runtime Memory Planning Gate text proving lifetime, allocation,
  budget, request, admission, and receipt evidence bindings without runtime
  handles
- a bounded Runtime Memory Planning matrix lookup that verifies graph family,
  source boundary, required artifact kinds, completeness, and exact artifact
  coverage
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
