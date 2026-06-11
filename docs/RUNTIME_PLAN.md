# Runtime Transfer Plan

TUC runtime planning now exposes data movement as concrete plan objects instead
of only aggregate counters.

## Why This Exists

Heterogeneous execution is only useful if the runtime can explain how tensors
move between memory domains and when layout conversion is required. Without an
explicit transfer plan, backend assignment can look correct while hiding the
cost of moving intermediate tensors through the memory hierarchy.

## Current Plan Objects

The first runtime plan objects live in `tuc.runtime.plan`:

- `RuntimeTransferEdge`: a tensor transfer between two backend memory domains.
- `LayoutConversionCost`: a tensor layout conversion required before an
  operation can consume a tensor.
- `TransferCostEstimate`: deterministic prototype bandwidth, latency, and
  energy estimate for a transfer edge.
- `TransferCostProfile`: validated per-domain transfer parameters that can be
  loaded from plain manifest data before runtime planning.

`PartitionPlan` now carries:

- Ordered backend assignments.
- Transfer edges.
- Layout conversion costs.
- Total transfer bytes.
- Total layout conversion bytes.
- Total explicit data movement bytes.
- Estimated total transfer latency.
- Estimated total transfer energy.

## Golden Dumps

Runtime plan text dumps are covered by golden fixtures in
`tests/golden/runtime_plans/`. The current fixtures cover default transfer
costing, backend-produced layout conversion, and calibrated transfer-cost
profiles.

Fixture updates are intentional compiler-contract changes. They should stay
small, readable, and tied to typed in-memory graph construction rather than
external generators.

Compiler decision reports complement runtime-plan dumps by showing which
registered backend capabilities accepted or rejected each operation before the
runtime assignment was finalized.

## Manual Override Policy

TUC accepts a first operation-scoped manual placement override data surface
through `RuntimeOverrideSet`.

Any future override mechanism must follow
[Runtime manual override policy](RUNTIME_OVERRIDE_POLICY.md). Overrides may only
constrain backend candidates that already passed capability diagnostics. They
cannot create backend capability facts, change operation semantics, mutate
HAC-IR, bypass validation, hide fallback behavior, or execute code.

Override effects are visible in compiler decision reports and deterministic
runtime-plan dumps through `manual_overrides` blocks.

## Candidate Score Diagnostics

TUC can emit opt-in candidate score diagnostics with
`include_candidate_scores=True` on `partition_graph(...)` or
`compile_graph(...)`.

Candidate scores are diagnostic data, not automatic global optimization. They
record the score components the current deterministic rule-based planner uses
when multiple accepted backend candidates remain:

- selection stage
- selected flag
- transfer score and unit
- transfer bytes
- layout conversion bytes
- preferred memory-domain match
- memory domain
- produced layout

Runtime-plan dumps include a `candidate_scores` block only when diagnostics are
enabled. Compiler decision reports carry the same evidence per operation.

Runtime Candidate Score Evidence adds a schema-versioned review artifact for
this boundary:

```bash
python examples/runtime_candidate_score_evidence.py
```

See [Runtime Candidate Score Evidence](RUNTIME_CANDIDATE_SCORE_EVIDENCE.md).

Runtime Candidate Scoring Policy fixes the accepted comparator order and keeps
future noise, error-budget, calibration, and benchmark score inputs blocked
until separate models exist:

```bash
python examples/runtime_candidate_scoring_policy.py
```

See [Runtime Candidate Scoring Policy](RUNTIME_CANDIDATE_SCORING_POLICY.md).

Runtime Candidate Scoring Conformance verifies that the current planner's
observable candidate choices match the active policy:

```bash
python examples/runtime_candidate_scoring_conformance.py
```

See
[Runtime Candidate Scoring Conformance](RUNTIME_CANDIDATE_SCORING_CONFORMANCE.md).

Runtime Candidate Scoring Gate composes score evidence, policy, and conformance
as the CI-facing check:

```bash
python examples/runtime_candidate_scoring_gate.py
```

See [Runtime Candidate Scoring Gate](RUNTIME_CANDIDATE_SCORING_GATE.md).

## Security Invariants

Runtime plan objects are declarative data:

- Names are validated.
- Memory domains and layouts are typed enums.
- Transfer and conversion byte counts must be positive and bounded.
- Transfer cost numbers must be finite and validated.
- Transfer-cost manifests are accepted only as bounded plain `dict`, `list`, and
  `tuple` data.
- Transfer-cost profile files must pass the schema-versioned JSON loader before
  becoming runtime profile data.
- Same-domain transfer edges are rejected.
- No plugin, backend, subprocess, import, or filesystem path is executed while
  constructing a plan or validating a transfer profile.
- Manual overrides are schema-versioned, bounded, operation-scoped, fail closed,
  and execution-free.
- Candidate score diagnostics are bounded, opt-in, and derived only from
  validated graph operations, capability data, movement estimates, transfer-cost
  profiles, and validated override effects.
- Candidate scoring policy is bounded data and keeps automatic global
  optimization plus noise/error-budget score components disabled in v0.
- Candidate scoring conformance is bounded data derived from typed in-memory
  planning fixtures; it does not add benchmark execution, backend execution, or
  plugin/device access.
- Candidate scoring gate is a read-only composition of score evidence, policy,
  and conformance for CI; it does not add new planning behavior.

## Current Limitations

This is still a prototype:

- Transfer cost uses a coarse deterministic prototype profile.
- Optional calibrated profiles can be loaded from schema-versioned JSON files.
- Layout conversion cost is byte-count based only.
- Synchronization, buffer lifetime, contention, calibration, and overlapping
  transfer/compute are future work.
- Graph input locations are assumed to start in row-major layout unless a
  future frontend/runtime contract states otherwise.

## Next Work

1. Include buffer lifetime and reuse in runtime planning.
2. Add benchmark hooks that compare transfer-aware and transfer-blind plans.
3. Add richer override diagnostics only if they stay bounded and visible in
   decision-report and runtime-plan golden fixtures.
4. Keep Runtime Candidate Scoring Conformance passing before changing
   comparator semantics.
5. Keep Runtime Candidate Scoring Gate passing in CI before accepting richer
   scoring behavior.
6. Add noise/error-budget candidate score components only after those models are
   stable and documented.
