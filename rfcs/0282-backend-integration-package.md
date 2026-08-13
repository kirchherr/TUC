# RFC 0282: Backend Integration Package v0

Status: Accepted

## Summary

Introduce a portable, data-only Backend Integration Package v0. It lets an
external backend author submit one bounded JSON document containing a Backend
Capability Manifest and positive and negative planning-conformance cases. TUC
validates the package and proves compiler selection without core changes,
plugin discovery, imports, backend code, or runtime execution.

## Motivation

TUC Master Plan Milestone 3 asks whether an external developer can integrate a
backend without modifying TUC core. Existing manifest and conformance paths
prove the internal interfaces, but their inputs are spread across project-owned
Python examples and fixtures. A portable vendor-facing artifact is needed to
test the architecture at its ownership boundary.

The package must increase portability without becoming an executable plugin
format. Treating untrusted package data as behavior would create import,
dependency, native-library, device, and confused-deputy attack surfaces before
the execution trust model is ready.

## Decision

Add:

- `docs/BACKEND_INTEGRATION_PACKAGE.md`
- `examples/backend_integration_package.py`
- `examples/backend_packages/external_vector.v0.json`
- `schemas/backend_integration_package.v0.schema.json`
- `schemas/backend_integration_package_report.v0.schema.json`
- `tests/golden/backend_integration_package/external_vector_report.json`
- `rfcs/0282-backend-integration-package.md`

The parser accepts exact, bounded plain JSON and delegates the inline capability
object to the same fail-closed parser used by standalone capability manifests.
Evaluation runs pure support diagnostics for every declared case and one
compiler planning probe derived by TUC from an accepted case.

A package passes only when:

- it has at least one accepted and one rejected case;
- every observed capability decision and rejection reason matches;
- the compiler assigns the generated probe to the declared backend;
- backend-code and execution-permission flags are false; and
- all blocked execution surfaces remain false in the report.

## Layer Ownership

- HAC-IR continues to express compute semantics only.
- Backend Capability describes supported operation kinds, layouts, memory, and
  quantitative limits.
- Backend Integration Package describes author-supplied capability and planning
  expectations.
- Compiler planning proves selection from capability data.
- Runtime and executable backend contracts remain unchanged and closed.

No vendor fact is added to HAC-IR and no backend implementation enters the
capability registry.

## Security Invariants

- Package loading is byte-bounded and duplicate-key rejecting.
- Parsing accepts exact plain JSON types, rejects unknown fields, and applies
  depth, collection, string, identifier, and case-count limits.
- Identifiers cannot select paths or modules.
- Package and report schemas reject additional properties.
- Source text, plugin entry points, commands, URLs, host paths, device IDs,
  runtime handles, generated code, native libraries, and backend artifacts are
  outside the contract.
- Evaluation performs no discovery, import, subprocess, network, device,
  artifact, or runtime operation.
- Passing evidence never grants executable-backend admission.

## Verification

The standard test suite covers the reference package, deterministic golden
output, in-memory capability-parser parity, schema closure, execution flags,
unknown execution-surface fields, path traversal, custom container types,
duplicate keys, excessive cases, and deliberate capability/conformance drift.

## Alternatives Rejected

### Python package or entry point

Rejected because importing untrusted vendor code makes description and
execution indistinguishable and expands the supply-chain attack surface.

### Native shared-library ABI

Rejected for v0 because ABI stability, process isolation, memory safety,
resource governance, artifact provenance, and device permissions require a
separate executable-backend RFC.

### Capability manifest without negative cases

Rejected because a list of positive claims cannot prove explicit rejection or
diagnostic behavior. At least one supported and one unsupported case are
required.

### Put vendor constraints in HAC-IR

Rejected because that would leak backend ownership into the hardware-neutral
semantic layer.

## Consequences

Master Plan Milestone 3 gains a concrete, externally reproducible
capability-and-planning proof. A backend author can produce one portable
artifact and receive deterministic integration evidence without a TUC core
change. Executable integration, native performance, and production hardware
support remain intentionally unproven.
