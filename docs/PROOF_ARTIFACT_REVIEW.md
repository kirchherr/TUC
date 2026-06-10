# Proof Artifact Review Checklist

This checklist applies to changes that modify Objective Alpha proof examples,
proof metadata, proof golden files, HAC-IR proof fixtures, runtime-plan proof
fixtures, or proof documentation.

Proof artifacts are public evidence for TUC's central claim. Reviewers should
treat updates as compiler-contract changes, not as ordinary snapshot churn.

## Applies To

Use this checklist when a pull request changes any of these paths:

```text
examples/proof_*.py
tests/golden/proofs/
tests/golden/hac_ir/proof_*.txt
tests/golden/runtime_plans/proof_*.txt
tests/golden/compiler_decisions/proof_*.txt
tests/test_proof_*.py
docs/PROOF_*.md
docs/PERFORMANCE_PROOF_READINESS.md
docs/PERFORMANCE_PROOF_RFC_REPORT.md
docs/PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT.md
docs/NATIVE_BASELINE_PROVENANCE.md
docs/NATIVE_BASELINE_COMPARISON_REPORT.md
docs/BREAK_EVEN_WORKLOAD_SIZE_REPORT.md
docs/EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md
docs/BENCHMARK_ARTIFACT_MANIFEST.md
docs/WORKLOAD_SCOPE_REPORT.md
docs/BENCHMARK_METHODOLOGY_REPORT.md
docs/TOOLCHAIN_ENVIRONMENT_REPORT.md
src/tuc/proof.py
```

## Required Reviewer Checks

Before approving a proof artifact change, reviewers should confirm:

- The PR explains which proof changed and why.
- The proof still strengthens hardware-independent compute rather than a
  backend-specific demo.
- The report metadata states `report_schema`, `proof_id`, `proof_version`,
  `graph_family`, and `backend_set`.
- `proof_version` changes when report meaning, graph semantics, or backend-set
  interpretation changes.
- `graph_family` matches the operation family being proven.
- `backend_set` is derived from the runtime partition plan and does not contain
  backend implementation details.
- HAC-IR changes preserve the semantic charter and do not add vendor, device,
  plugin, generated-artifact, benchmark, calibration, or runtime-handle data.
- Runtime-plan changes keep backend assignments, transfer bytes, movement
  costs, and fallback reasons inspectable.
- Compiler decision-report changes keep accepted backends, rejected backends,
  assignment reasons, and fallback support evidence inspectable.
- Numerical results are compared against deterministic independent reference
  semantics.
- Full proof stdout, HAC-IR dump, runtime-plan dump, and compiler
  decision-report golden files are updated together when the proof contract
  changes.
- The proof still ends with `PASS`.
- Tests cover the changed golden artifacts.
- The proof does not claim native performance parity, 100 percent native
  performance, or a fixed percentage of vendor-library performance unless
  [Performance Proof Boundary](PERFORMANCE_PROOF_BOUNDARY.md) is satisfied.
- Future native performance claims pass the
  [Performance Proof Readiness Report](PERFORMANCE_PROOF_READINESS.md) and do
  not include raw benchmark output in readiness evidence.
- Future native performance claims include a bounded
  [Performance Proof RFC Report](PERFORMANCE_PROOF_RFC_REPORT.md) before
  benchmark artifacts are interpreted as proof evidence.
- Future native performance claims include a bounded
  [Performance Claim Threshold Policy Report](PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT.md)
  before "near native" or percentage claims are reviewed.
- The proof does not claim 100 percent native performance.

## Security Checks

Proof artifacts must not introduce:

- Backend plugin discovery.
- Dynamic imports of user-controlled modules.
- Subprocesses except the existing test execution of repository-owned proof
  examples.
- Dynamic libraries.
- Device access.
- Network access.
- Generated-artifact execution.
- Host-path leakage in proof output.
- Environment-variable-dependent proof behavior.
- Hidden planner overhead or performance timing reported as correctness proof.

Any exception requires a dedicated security RFC, threat model, resource budget,
and sandboxing plan before merge.

## Performance Claim Checks

Current Objective Alpha proof artifacts are correctness and inspectability
evidence, not performance evidence.

Reviewers should reject proof changes that claim native performance parity until
the performance proof boundary and readiness report supply:

- native baseline provenance
- performance proof RFC report
- performance claim threshold policy report
- native baseline provenance report
- native baseline comparison report
- workload scope report
- benchmark methodology report
- toolchain environment report
- leaky-abstraction report
- planner-overhead report
- break-even workload-size report
- benchmark methodology
- correctness goldens for benchmarked workloads
- runtime-plan and compiler decision-report goldens
- deterministic benchmark report artifacts
- benchmark artifact manifest
- executable backend security review report

## Required Validation

Run the narrow proof checks first:

```bash
python -m pytest tests/test_proof_metadata.py tests/test_proof_of_abstraction.py tests/test_proof_of_reduction.py tests/test_proof_of_softmax.py tests/test_hac_ir_golden_dumps.py tests/test_runtime_plan_golden.py tests/test_compiler_decision_report_golden.py -q
```

Then run the normal project checks:

```bash
python -m ruff check .
python -m mypy src/tuc
python -m pytest -q
python examples/proof_of_abstraction.py
python examples/proof_of_reduction.py
python examples/proof_of_softmax.py
```

## Golden File Discipline

Golden proof updates are acceptable only when the PR also explains the contract
change. Reviewers should inspect the textual diff rather than approving golden
files as generated noise.

Do not regenerate proof goldens as a cleanup step. Update them only when the
intended proof behavior, metadata contract, HAC-IR contract, or runtime-plan
contract, or compiler decision-report contract changed.

## Merge Gate

A proof artifact PR is ready to merge when:

- The checklist questions are answered in the PR body or linked RFC.
- Required tests pass.
- The changed proof remains reproducible without real hardware.
- The security checks above are satisfied.
- Any future work is tracked in the roadmap or a follow-up RFC.
