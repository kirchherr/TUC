# Objective Delta Installed Portable Compute

Objective Delta joins TUC's installed distribution boundary to its controlled
heterogeneous runtime proof. It is the first public installed-wheel path that
starts with external plain data and finishes with trusted execution evidence.

## Research Question

Can an external consumer use a built TUC distribution to express one bounded
compute intent, combine two hardware-neutral backend capability packages, and
obtain a correct heterogeneous result without importing repository code or
executing package-provided code?

For the fixed Objective Delta v0 proof, the answer is **PASS**.

## Installed Proof

The proof path is:

```text
built TUC wheel
    -> isolated external consumer
    -> bounded Source Intent JSON
    -> two external data-only backend packages
    -> external-systolic -> external-vector source plan
    -> fixed trusted simulator projection
    -> blocked -> row_major layout conversion
    -> controlled execution
    -> independent reference correctness
    -> reference-cpu backend equivalence
    -> digest-only PASS report
```

`scripts/verify_external_portable_compute_consumer.py` builds the isolation
boundary around `integration/objective_delta`. It validates an exact audited
file set and pinned consumer digest, installs the wheel without dependency
resolution, proves that `tuc` resolves outside the source tree, removes import
path overrides, and runs both the public Python API and installed CLI. Both
surfaces must reproduce `integration/objective_delta/expected_report.json`
byte for byte.

The source package order is deliberately reversed by the standalone consumer.
The public API canonicalizes package identity before planning, so filesystem or
argument order cannot redefine the proof.

## Public Contract

External consumers use:

```python
from tuc.portable_compute import prove_portable_compute

report = prove_portable_compute(
    "source_intent.v0.json",
    ("external_systolic.v0.json", "external_vector.v0.json"),
)
assert report["proof_status"] == "PASS"
```

The installed CLI is:

```bash
tuc-prove-portable-compute \
  source_intent.v0.json \
  external_systolic.v0.json \
  external_vector.v0.json
```

The API and report contracts are versioned independently. Rejected CLI inputs
return a fixed source-free error and never echo paths, payloads, parser
diagnostics, or tensor values.

## Trusted Projection

The external packages declare capability data only. Objective Delta binds the
exact admitted package identities and digests to this reviewed projection:

```text
external-systolic -> systolic-sim
external-vector   -> vector-sim
```

Both target executors already live in TUC's fixed trusted executor registry.
The report preserves the external source plan and the trusted execution plan as
separate identities. Projection therefore cannot be confused with loading or
running an external backend implementation.

## Security Boundary

Objective Delta preserves these invariants:

- Source Intent and backend packages are bounded, explicit, non-symlink JSON
  files with exact accepted identities and shapes.
- No package discovery, dynamic import, entry-point loading, generated code,
  native library, network, command, device path, or external runtime handle is
  admitted.
- Runtime tensor values exist only inside the trusted process and are not
  serialized into evidence.
- The standalone consumer imports only `tuc.portable_compute` from TUC.
- Fixed internal input values make the proof reproducible without turning
  arbitrary external tensors into a new public attack surface.
- Independent reference correctness and backend equivalence must both pass.
- The report schema is closed and binds source, packages, plans, placement,
  layout conversion, execution, and comparison through metadata digests.

## Claim Boundary

Objective Delta is Level 4 integration evidence for one bounded portable
compute slice. It proves that the same neutral intent can cross an installed
public interface, be planned from external capability data, execute through
reviewed trusted prototype backends, and preserve observable semantics.

It does not prove arbitrary source parsing, arbitrary graph execution,
executable plugins, vendor implementations, native lowering, physical devices,
competitive performance, publication, or independent organizational adoption.
Those remain separate proof classes.

## Verification

- `src/tuc/portable_compute.py`
- `integration/objective_delta`
- `schemas/portable_compute_proof_report.v0.schema.json`
- `scripts/verify_external_portable_compute_consumer.py`
- `tests/test_portable_compute.py`

Decision: `rfcs/0292-objective-delta-installed-portable-compute.md`.
