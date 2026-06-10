# Backend Author Certification

Backend author certification is TUC's review checklist for prototype backends.
It is not a legal certification and it is not a hardware conformance program.
It is the minimum evidence a backend author must provide before maintainers
should trust a backend experiment.

## Certification Goal

A backend proposal must prove three things:

- The backend declares its capability surface as data.
- The backend rejects unsupported work before lowering.
- The backend does not add a compiler-time execution surface.

Backend API v0.1 remains capability-first. No plugin discovery, import hook,
dynamic library loading, subprocess execution, device access, artifact
execution, or network access is part of certification.

## Required Evidence

Every backend proposal must include:

- A schema-versioned backend capability manifest.
- A passing Manifest Claim Review report for that manifest.
- A description of supported operations and numeric semantics.
- Accepted layouts and produced layouts.
- Memory domain and transfer assumptions.
- Error-budget behavior.
- Latency, energy, calibration, and noise-model assumptions, documented using
  [Backend Capability Schema](BACKEND_CAPABILITY_SCHEMA.md).
- Deterministic diagnostics for rejected operations.
- Negative tests for malformed manifests and unsupported operations.
- A statement that capability checks are pure data checks.

## Capability Checklist

Backend capability data must satisfy:

- `name` is stable and simple.
- `supported_ops` contains only operation families the backend truly accepts.
- `preferred_for` is a subset of `supported_ops`.
- `supported_layouts` lists layouts accepted as inputs.
- `produced_layouts` lists layouts emitted by the backend.
- `memory_domain` matches where outputs reside after backend execution.
- `max_error_budget` is finite, non-negative, and documented when present.
- `supports_noise_model` and `supports_calibration` are truthful prototype
  claims, not marketing flags.

## Lowering Checklist

Backend lowering must:

- Accept only validated graph objects.
- Check `capability.supports(operation)` for every operation before artifact
  emission.
- Reject unsupported operations with deterministic diagnostics.
- Keep layout conversion visible to TUC instead of hiding it inside backend
  code.
- Emit artifacts as data, not executed code.
- Avoid reading files, environment variables, or device state unless a later
  backend lifecycle RFC explicitly permits that path.

## Manifest Checklist

Backend capability manifests must not contain:

- Python module names.
- Import paths.
- Shell commands.
- Device paths.
- Dynamic library paths.
- Plugin entry points.
- Network endpoints.
- Environment-variable names.
- Cache or artifact output paths.

If a backend needs any of those fields, it needs a new security RFC before the
field can enter the schema.

## Negative Test Requirements

Backend authors must copy or adapt the executable template in:

```text
tests/test_backend_author_negative_template.py
```

At minimum, their tests must prove:

- Plugin-like manifest fields are rejected.
- Duplicate manifest keys are rejected.
- Unsupported schema versions are rejected.
- `preferred_for` cannot claim unsupported operations.
- Unsupported operation layouts are not accepted by capability checks.
- Backend lowering rejects operations outside the declared capability set.

These tests should be submitted before any backend-specific lowering code.

Backend authors should also compare their manifests against the invalid and
misleading examples in [Backend Capability Schema](BACKEND_CAPABILITY_SCHEMA.md).
Claims about latency, energy, calibration evidence, hardware certificates,
benchmark scores, or measured accuracy do not belong in
`tuc.backend_capability.v0`.

## Manifest Claim Review Requirements

Backend authors must run [Manifest Claim Review](MANIFEST_CLAIM_REVIEW.md)
before maintainers treat a manifest as planning evidence.

The reference author path runs this automatically:

```bash
python examples/external_backend_author_path.py
```

That path stops before registry loading, compiler planning, conformance, or
trusted lowering when the manifest claim review fails.

Authors can also inspect the standalone review suite:

```bash
python examples/manifest_claim_review.py
```

The external author path stores deterministic golden evidence for the toy
backend at:

```text
tests/golden/backend_claim_review/external_vector_author_report.json
```

## Conformance Fixture Requirements

Backend authors must also add a positive/rejection conformance test using:

```python
from tuc.backends.conformance import assert_backend_conformance


def test_backend_conformance() -> None:
    assert_backend_conformance(backend)
```

The reusable fixtures are documented in
[Backend Conformance Fixtures](BACKEND_CONFORMANCE.md). They verify that
declared capability data and lower-time behavior agree for MVP operation
fixtures.

Authors can use the external-style path in
`examples/external_backend_author_path.py` as the reference shape for a toy
backend proposal. The corresponding test,
`tests/test_external_backend_author_path.py`, proves that manifest claim review,
manifest loading, registry diagnostics, compiler planning, conformance, and
trusted lowering can work without modifying TUC core or adding plugin
discovery.

## Review Outcome

Maintainers should block a backend proposal when:

- Capability checks execute backend code.
- Unsupported operations are silently emulated or routed through implicit
  fallback that changes semantics.
- Manifest data includes executable hooks or host paths.
- Backend artifacts are executed during compile, validation, partitioning, or
  tests.
- Diagnostics hide why an operation was rejected.
- Resource limits are undefined or untested.

## Future Certification Work

Before TUC accepts real third-party plugins, certification must grow to include:

- Plugin lifecycle threat model.
- Sandboxed execution policy.
- Artifact provenance and signing.
- Native-code sanitizer and fuzzing requirements.
- Backend conformance suite.
- Revocation or quarantine process for vulnerable backend releases.
