# Runtime Candidate Scoring Gate

Runtime Candidate Scoring Gate v0 is the CI-facing check for the current
runtime candidate-scoring evidence surface.

It runs:

- `build_profiled_candidate_score_evidence_report()`
- `build_runtime_candidate_scoring_policy_report()`
- `run_runtime_candidate_scoring_conformance()`
- `examples/runtime_candidate_scoring_gate.py`

The gate passes only when:

- Runtime Candidate Score Evidence passes
- Runtime Candidate Scoring Policy is complete
- Runtime Candidate Scoring Conformance passes

Golden output:

```text
tests/golden/runtime_candidate_scoring_gate/current_gate.txt
```

CI entry:

```text
.github/workflows/ci.yml
```

## Security Boundary

The gate composes bounded data-only reports. It does not discover plugins,
import backend modules, load dynamic libraries, spawn subprocesses outside the
example process, access devices, touch the network, execute generated
artifacts, run JIT code, read host paths, read environment variables, load raw
benchmark output, or authorize executable backend surfaces.

## Review Meaning

The gate is not a native performance claim and not a global optimizer. It is a
merge-time confidence check that candidate-score diagnostics remain
inspectable, the active comparator policy is explicit, and the planner's
observable behavior still conforms to that policy.
