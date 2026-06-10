# Manifest Claim Review

Manifest Claim Review v0 is a data-only maintainer review artifact for backend
capability manifests.

It sits after manifest loading:

```text
explicit manifest path -> bounded manifest loader -> typed capability ->
manifest claim review report
```

The loader rejects malformed or unsupported fields. The claim review report
adds a second check for manifests that are syntactically valid but strategically
too broad or semantically risky.

## Contract

- Report schema: `schemas/manifest_claim_review_report.v0.schema.json`
- Report schema version: `tuc.manifest_claim_review_report.v0`
- Contract: `manifest_claim_review.data_only.v0`
- Example: `examples/manifest_claim_review.py`
- Golden: `tests/golden/backend_claim_review/manifest_claim_review_report.json`
- Tests: `tests/test_manifest_claim_review.py`

## Current Review Rules

The v0 review blocks:

- manifests rejected by the bounded backend capability loader
- non-`reference-cpu` backends that claim all current MVP operation families
- `reference-cpu` manifests that claim a non-`host_ram` memory domain
- noise-model claims without an explicit `max_error_budget`
- calibration claims without an explicit `max_error_budget`
- non-`reference-cpu` host-memory backends that claim specialized blocked
  output layout

These rules do not certify accepted manifests. They only say that the manifest
passed the current claim-shape review.

## Negative Fixtures

The current suite includes:

- `examples/manifests/review/invalid_executable_surface_backend.json`
- `examples/manifests/review/invalid_noise_without_error_budget_backend.json`
- `examples/manifests/review/invalid_overbroad_accelerator_backend.json`

The suite expects those manifests to be `blocked`. A report can still pass when
negative fixtures are blocked as expected.

## Security Boundary

Manifest Claim Review uses explicit file paths supplied by the caller. It does
not scan directories, import backend modules, discover plugins, instantiate
backend objects, load dynamic libraries, spawn subprocesses, access devices,
touch the network, execute generated artifacts, run JIT code, parse source
text, or include host paths in the report.

Report fields are bounded identifiers. Loader failures are represented by issue
codes, not raw exception strings or local path details.

## Reviewer Checklist

Before accepting a new specialized accelerator manifest, verify:

- The manifest is accepted by the bounded loader.
- The manifest claim review status is `accepted`.
- Broad operation-family support has a separate RFC and conformance evidence.
- Noise or calibration claims include an explicit error-budget boundary.
- Runtime execution remains authorized only by trusted runtime executor
  contracts.
- HAC-IR remains free of backend-specific details.

## Backend Author Path

`examples/external_backend_author_path.py` runs Manifest Claim Review as its
first gate. A backend author manifest must be `accepted` before the path loads
the manifest into `BackendRegistry`, compiles the example graph, runs backend
conformance, or lowers the assigned HAC-IR subgraph.

The toy author path has its own deterministic golden at:

```text
tests/golden/backend_claim_review/external_vector_author_report.json
```

The complete author path is summarized by
[Backend Author Readiness](BACKEND_AUTHOR_READINESS.md).
