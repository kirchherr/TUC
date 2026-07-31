# Backend Integration Package

Backend Integration Package v0 is the portable, data-only entry point for an
external backend author. It proves that a vendor capability can be validated,
diagnosed, and selected by the compiler without modifying TUC core and without
loading or executing vendor code.

## Research Question

Can an external developer describe a backend and its positive and negative
planning expectations through a stable hardware-neutral interface?

The bounded v0 answer is yes for capability and planning conformance. The
reference package is
`examples/backend_packages/external_vector.v0.json`; TUC turns it into a
deterministic report through `examples/backend_integration_package.py`.

## Contract

One package contains only:

- a schema version, package identity, and fixed data-only policies;
- one inline Backend Capability Manifest;
- bounded positive and negative conformance cases;
- explicit declarations that backend code and execution permission are absent.

The validation flow is:

```text
vendor JSON
    -> bounded fail-closed parser
    -> BackendCapability
    -> registry support diagnostics
    -> compiler planning probe
    -> deterministic integration report
```

The planning probe is constructed by TUC from one accepted case. A passing
report requires every support expectation to match and the compiler to assign
the probe operation to the package's declared backend.

## Security Boundary

The package is data, never a delivery mechanism for behavior. Validation:

- accepts only plain JSON objects and arrays within fixed size and depth limits;
- rejects duplicate keys, unknown fields, path-like identifiers, and unsupported
  schema versions;
- performs no plugin discovery, dynamic import, native-library loading,
  subprocess execution, network access, device access, runtime execution, or
  generated-artifact execution;
- does not accept source text, entry points, host paths, device identifiers,
  runtime handles, commands, URLs, or backend artifacts;
- records all blocked execution surfaces in the deterministic report.

An executable implementation remains a separate trust decision. Passing this
contract does not grant execution permission.

## Run

```bash
python examples/backend_integration_package.py
```

The output should match
`tests/golden/backend_integration_package/external_vector_report.json` and end
with `integration_status` set to `PASS`.

## Artifacts

- Package schema: `schemas/backend_integration_package.v0.schema.json`
- Report schema: `schemas/backend_integration_package_report.v0.schema.json`
- Reference package: `examples/backend_packages/external_vector.v0.json`
- Entrypoint: `examples/backend_integration_package.py`
- Golden report: `tests/golden/backend_integration_package/external_vector_report.json`
- Decision record: `rfcs/0282-backend-integration-package.md`

## Non-Claims

Backend Integration Package v0 does not define a binary ABI, package discovery,
plugin installation, executable backend admission, device enumeration, native
lowering, performance parity, or production hardware support. It closes the
capability-and-planning portion of the external backend author test only.
