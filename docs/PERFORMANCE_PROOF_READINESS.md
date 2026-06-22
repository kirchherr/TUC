# Performance Proof Readiness Report

Performance Proof Readiness is a deterministic review report for future native
performance proof proposals.

It does not run benchmarks, ingest benchmark artifacts, access devices, inspect
host hardware, execute backend artifacts, execute generated code, discover
plugins, load dynamic libraries, run subprocesses, or claim native performance
parity.

The readiness report does not access devices.
The readiness report does not execute backend artifacts.
The readiness report does not claim native performance parity.

## Contract

- Boundary contract: `performance_proof_boundary.blocking.v0`
- Report schema version: `tuc.performance_proof_readiness_report.v0`
- Evidence type: `PerformanceProofReadinessEvidence`
- API: `build_performance_proof_readiness_report(proposal_name, evidence)`
- Assertion API: `assert_performance_proof_readiness(proposal_name, evidence)`
- Dump API: `dump_performance_proof_readiness_report(report)`
- Required evidence IDs: `PERFORMANCE_PROOF_REQUIRED_EVIDENCE`
- Blocked claims: `PERFORMANCE_PROOF_BLOCKED_CLAIMS`
- Example: `examples/performance_proof_readiness.py`
- Golden: `tests/golden/proofs/performance_proof_readiness_report.json`
- Tests: `tests/test_performance_proof_readiness.py`
- Next gate: [Performance Proof Interpretation](PERFORMANCE_PROOF_INTERPRETATION.md)
- Next gate schema: `schemas/performance_proof_interpretation_report.v0.schema.json`

The report is ready only when every required evidence ID is present. A ready report is metadata-complete; it is not a benchmark interpretation, execution grant, or native performance proof. The next review step is the data-only Performance Proof Interpretation report.

## Required Evidence

The readiness report tracks:

- performance proof RFC
- performance claim threshold policy
- performance acceptance criteria
- benchmark methodology
- native baseline provenance
- versioned toolchain environment
- workload scope
- correctness goldens
- native baseline comparison
- leaky-abstraction report
- planner-overhead report
- break-even workload-size report
- runtime-plan goldens
- compiler decision-report goldens
- benchmark report schema
- benchmark report artifacts
- executable backend security review

Missing evidence keeps native performance claims blocked.

The current diagnostic performance proof RFC report schema is
`schemas/performance_proof_rfc_report.v0.schema.json`. It can satisfy only the
existence of a bounded claim-proposal metadata contract. It does not run
benchmarks, load benchmark artifacts, grant execution permission, or prove
native performance parity.

The current diagnostic performance claim threshold policy report schema is
`schemas/performance_claim_threshold_policy_report.v0.schema.json`. It can
satisfy only the existence of a bounded threshold-policy metadata contract. It
does not run benchmarks, evaluate raw timing samples, grant execution
permission, or prove native performance parity.

The current diagnostic performance acceptance criteria report schema is
`schemas/performance_acceptance_criteria_report.v0.schema.json`. It can satisfy
only the existence of a bounded acceptance-criteria metadata contract. It does
not run benchmarks, evaluate raw timing samples, grant execution permission, or
prove native performance parity.

The current readiness example marks `performance_proof_rfc`,
`performance_claim_threshold_policy`, and `performance_acceptance_criteria`
present only after binding every accepted Kernel Ingress workload scope to
accepted, digest-pinned governance reports. Those reports define proposal,
threshold, and pass/fail metadata before benchmark artifacts can be interpreted.
They keep `native_performance_claim` false and do not load evidence, run
benchmarks, grant execution permission, or approve executable backend surfaces.

The current diagnostic CPU baseline report schema is
`schemas/baseline_benchmark_report.v0.schema.json`. It can satisfy only the
existence of a bounded report schema for the baseline harness. It does not
satisfy native baseline comparison, planner-overhead report,
leaky-abstraction report, benchmark report artifacts, or executable backend
security review.

The current diagnostic workload scope report schema is
`schemas/workload_scope_report.v0.schema.json`. It can satisfy only the
existence of a bounded workload-scope contract. It does not satisfy benchmark
methodology, native baseline comparison, benchmark artifacts, execution timing,
or native performance parity.

The current Kernel Ingress workload-scope binding is
`examples/source_to_intent_research_kernel_ingress_workload_scope.py`. It can
mark `workload_scope` as present for readiness review by binding accepted
Kernel Ingress shape-profile evidence to diagnostic workload scopes.

The readiness example derives `benchmark_methodology` from those same Kernel
Ingress workload scopes. It builds bounded methodology entries that define the
clock, warmup and measurement iteration policy, statistic policy, isolation,
outlier policy, and reproducibility policy before any benchmark artifact can
count as evidence. This does not run benchmarks or ingest timing samples.

The current diagnostic benchmark methodology report schema is
`schemas/benchmark_methodology_report.v0.schema.json`. It can satisfy only the
existence of a bounded benchmark methodology contract. It does not run
benchmarks, load benchmark artifacts, validate raw native output, or prove
native performance parity.

The current diagnostic toolchain environment report schema is
`schemas/toolchain_environment_report.v0.schema.json`. It can satisfy only the
existence of a bounded versioned toolchain environment contract. It does not
inspect the host, read environment variables, run discovery commands, access
devices, or prove native performance parity.

The current readiness example marks `versioned_toolchain_environment` present
only after building a Toolchain Environment Report from repository-controlled
version declarations and file digests: the GitHub Actions Python runtime policy,
`pyproject.toml` package metadata, `requirements/dev.txt` development dependency
metadata, the dev Dockerfile, the native compiler policy declared by that
Dockerfile, and `docker-compose.yml`. Each component must carry a `sha256:`
digest of its repository file. The check does not collect host package versions,
read environment variables, inspect devices, run discovery commands, or turn
unlocked dependency declarations into native baseline provenance.

The current diagnostic planner-overhead report schema is
`schemas/planner_overhead_report.v0.schema.json`. It can satisfy only the
existence of a bounded planner phase-separation report. It does not satisfy
break-even workload-size evidence, execution timing evidence, native baseline
comparison, or native performance parity.

The current readiness example builds a bounded planner-overhead report for the
accepted Kernel Ingress MVP pipeline graph and checks the report contract before
marking `planner_overhead_report` present. It verifies that planner overhead is
not hidden inside execution time, execution timing remains unmeasured, and
break-even evidence remains not established. It does not publish raw timings,
run benchmarks, execute backend artifacts, or create a native performance
claim.

The same readiness example also verifies the deterministic Kernel Ingress
golden at `tests/golden/frontend/source_to_intent_research_kernel_ingress.json`
before marking `correctness_goldens`, `runtime_plan_goldens`, and
`compiler_decision_report_goldens` present. The check requires each accepted
case to expose the corresponding SHA-256 digest field while keeping raw source
and raw tensor values out of the readiness output.

The readiness example verifies
`schemas/baseline_benchmark_report.v0.schema.json` before marking
`benchmark_report_schema` present. The schema must remain fail-closed,
diagnostic-only, bound to `performance_proof_boundary.blocking.v0`, and must
forbid native performance claims. This schema check is separate from benchmark
artifact inventory and does not accept measured benchmark results as proof
evidence.

The current diagnostic break-even workload-size report schema is
`schemas/break_even_workload_size_report.v0.schema.json`. It can satisfy only
the existence of a bounded break-even workload-size metadata contract. It does
not run benchmarks, load benchmark artifacts, ingest raw timing samples, or
prove native performance parity.

The current readiness example marks `break_even_workload_size` present only
after binding every accepted Kernel Ingress workload scope to an
`estimated_not_validated` break-even entry. The entry uses the workload scope's
bounded maximum problem size as the estimate, references the Kernel Ingress
planner-overhead report ID, omits evidence digests, and keeps
`break_even_workload_size_ready` false. This proves only that future benchmark
artifacts have an amortization review surface; it does not validate break-even
sizes, compare timing samples, load benchmark artifacts, or claim planner
benefit.

The current diagnostic leaky-abstraction report schema is
`schemas/leaky_abstraction_report.v0.schema.json`. It can satisfy only the
existence of a bounded HAC-IR boundary review report. It does not satisfy
native baseline comparison, benchmark artifacts, or native performance parity.

The readiness example derives `leaky_abstraction_report` from the accepted
Kernel Ingress MVP pipeline graph. It verifies that HAC-IR remains contract
valid, no forbidden hardware-specific attributes enter HAC-IR, and performance
facts such as tile shape, vector width, transfer latency, and backend sequence
choice stay in backend capabilities, backend implementations, runtime plans, or
compiler decision reports. Native baseline and native performance claims remain
separate blockers.

The current diagnostic native baseline provenance report schema is
`schemas/native_baseline_provenance_report.v0.schema.json`. It can satisfy only
the existence of a bounded native baseline provenance contract. It does not
satisfy native baseline comparison, benchmark report artifacts, execution
timing, or native performance parity.

The current readiness example marks `native_baseline_provenance` present only
after binding every accepted Kernel Ingress workload scope to a data-only native
baseline candidate. The candidates use a portable CPU native-library target ID,
are marked `documented_not_executed`, omit artifact digests, and keep
`native_baseline_ready` false. This proves only that future comparisons have a
bounded provenance surface; it does not reproduce native baselines, load native
artifacts, compare benchmark results, or make a native performance claim.

The current diagnostic native baseline comparison report schema is
`schemas/native_baseline_comparison_report.v0.schema.json`. It can satisfy only
the existence of a bounded native comparison metadata contract. It does not
load benchmark artifacts, parse raw benchmark output, store timing samples, or
prove native performance parity.

The current readiness example marks `native_baseline_comparison` present only
after binding every accepted Kernel Ingress workload scope to a data-only native
comparison reference. Each comparison is `not_measured`, carries no comparison
digest, and keeps `native_baseline_comparison_ready` false. This proves only
that future benchmark artifacts have a bounded comparison surface; it does not
load artifacts, validate CI benchmark output, compare timing samples, or make a
native performance claim.

The current diagnostic benchmark artifact manifest report schema is
`schemas/benchmark_artifact_manifest_report.v0.schema.json`. It can satisfy only
the existence of a bounded benchmark artifact inventory contract. It does not
load benchmark artifacts, satisfy benchmark result acceptance, validate raw
native output, or prove native performance parity.

The current readiness example marks `benchmark_report_artifacts` present only
after binding all required benchmark artifact kinds to repository-golden
descriptors with SHA-256 digests. Those descriptors are inventory review
objects, not raw benchmark reports. The readiness example does not parse
benchmark artifact contents, load raw output, validate native timings, or accept
benchmark results as proof.

The current diagnostic executable backend security review report schema is
`schemas/executable_backend_security_review_report.v0.schema.json`. It can
satisfy only the existence of a bounded executable-surface security review
metadata contract. It does not execute backend artifacts, access devices, load
dynamic libraries, run subprocesses, discover plugins, approve execution, or
approve native performance parity.

The current readiness example marks `executable_backend_security_review`
present only after building a complete Executable Backend Security Review
Report over every tracked executable surface, binding each entry to threat
model, sandbox model, resource budget, provenance, negative-test evidence, and
a repository RFC digest. This makes the readiness report metadata-complete for
the current Kernel Ingress proof slice, but it does not grant runtime execution
permission or prove native performance parity.

## Blocked Claims

The v0 report explicitly blocks:

- native performance parity
- 100 percent native performance
- fixed vendor performance percentages
- near-native claims without a predefined threshold
- hidden planner overhead inside execution time
- transfer estimates treated as measured hardware performance
- hardware-specific HAC-IR knobs

These blocked claims mirror the
[Performance Proof Boundary](PERFORMANCE_PROOF_BOUNDARY.md).

## Security Boundary

The readiness report accepts only explicit evidence IDs and booleans. It must
not include raw benchmark output, raw timing samples, host paths, environment
variables, hardware serials, device identifiers, generated artifacts, plugin
entrypoints, backend binaries, dynamic-library paths, cache paths, or backend
artifact contents.

The readiness report must not include raw benchmark output.

Unknown evidence IDs and duplicate evidence IDs fail closed.

The report is not a benchmark schema and is not a benchmark result format. A
future benchmark report schema must be reviewed separately before benchmark
artifacts can become proof evidence.

The readiness report is not a performance proof RFC report. Native performance
claim proposals are tracked by
[Performance Proof RFC Report](PERFORMANCE_PROOF_RFC_REPORT.md), which is
data-only and remains separate from benchmark artifacts, execution permission,
and native performance proof.

The readiness report is not a performance claim threshold policy report. Claim
thresholds are tracked by
[Performance Claim Threshold Policy Report](PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT.md),
which is data-only and remains separate from benchmark execution and measured
results.

The readiness report is not a performance acceptance criteria report. Claim
pass/fail criteria are tracked by
[Performance Acceptance Criteria Report](PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT.md),
which is data-only and remains separate from benchmark execution and measured
results.

The readiness report is also not a native baseline provenance report. Native
baseline candidates are tracked by
[Native Baseline Provenance Report](NATIVE_BASELINE_PROVENANCE.md), which is
data-only and remains claim-blocked in v0.

The readiness report is not a native baseline comparison report. Native
comparison metadata is tracked by
[Native Baseline Comparison Report](NATIVE_BASELINE_COMPARISON_REPORT.md), which
is data-only and remains separate from raw benchmark values.

The readiness report is not a benchmark artifact manifest. Benchmark report
artifact inventory is tracked by
[Benchmark Artifact Manifest Report](BENCHMARK_ARTIFACT_MANIFEST.md), which is
data-only and remains separate from benchmark result validation.

The readiness report is not a workload scope report. Workload boundaries are
tracked by [Workload Scope Report](WORKLOAD_SCOPE_REPORT.md), which is
data-only and remains separate from benchmark methodology and execution.

The readiness report is not a benchmark methodology report. Measurement policy
is tracked by
[Benchmark Methodology Report](BENCHMARK_METHODOLOGY_REPORT.md), which is
data-only and remains separate from benchmark execution and raw timing samples.

The readiness report is not a toolchain environment report. Versioned toolchain
inventory is tracked by
[Toolchain Environment Report](TOOLCHAIN_ENVIRONMENT_REPORT.md), which is
data-only and remains separate from host discovery.

The readiness report is not a break-even workload-size report. Break-even
metadata is tracked by
[Break-Even Workload Size Report](BREAK_EVEN_WORKLOAD_SIZE_REPORT.md), which is
data-only and remains separate from raw timing samples.

The readiness report is not an executable backend security review report.
Executable-surface security evidence is tracked by
[Executable Backend Security Review Report](EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md),
which is data-only and remains separate from execution permission.

## Evidence

The current golden report is metadata-complete for the Kernel Ingress proof
slice:

```text
tests/golden/proofs/performance_proof_readiness_report.json
```

This makes the current roadmap state explicit: TUC has a performance proof
boundary, a readiness report, accepted governance metadata, bounded Kernel
Ingress workload-scope evidence, digest-bound benchmark artifact inventory, and
a digest-bound executable backend security review. Native performance claims
remain blocked because readiness is not a benchmark result, execution grant, or
native performance proof. `examples/performance_proof_interpretation.py` records
that next gate explicitly: readiness is true, but measurement interpretation is
not supplied.

## Still Blocked

These remain blocked after this report exists:

- claiming native performance parity
- claiming 100 percent native performance
- claiming a fixed percentage of CUDA, HIP, vendor-library, or hand-optimized
  kernel performance
- claiming near-native performance without a predefined threshold
- hiding planner overhead inside execution timing
- treating transfer-cost estimates as measured hardware performance
- executing backend artifacts or device code as part of proof review
- adding hardware-specific performance knobs to HAC-IR
