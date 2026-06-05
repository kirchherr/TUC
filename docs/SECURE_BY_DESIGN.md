# Secure By Design

TUC is a compiler and runtime project. Compilers process attacker-controlled
programs, graphs, IR, metadata, and backend descriptions. TUC must therefore be
designed as a security-sensitive system from the beginning.

## Security Objective

No TUC feature may create an avoidable path from untrusted input to:

- arbitrary host code execution,
- arbitrary filesystem writes,
- arbitrary network access,
- unbounded resource consumption,
- silent wrong-code generation,
- secret leakage, or
- unauthorized backend/device access.

## Trust Boundaries

Treat these as untrusted:

- Triton/Python source and source-derived metadata.
- IR text and serialized graphs.
- Tensor shapes, dtypes, attributes, and model metadata.
- Backend manifests and capability declarations.
- Runtime execution plans.
- Cache keys and cache contents.
- Environment variables and config files.
- CI inputs, pull request content, and generated artifacts.

## Design Rules

### Parse Data, Not Behavior

Parsing, validation, IR dumping, backend discovery, and capability matching must
not execute user-controlled code.

Disallowed by default:

- `eval` or equivalent dynamic evaluation.
- untrusted Python imports during compiler discovery,
- shelling out with user-controlled data,
- loading dynamic libraries from untrusted paths,
- network access during compile,
- plugin code execution during capability validation.

### Validate Before Lowering

Every public input boundary needs schema validation before lowering:

- operation kind,
- tensor rank and dimensions,
- dtype,
- attribute names and value types,
- resource budgets,
- backend capability claims,
- target-specific constraints.

Malformed input must fail closed with structured diagnostics.

### Bound Resource Use

Every accepted input format must have explicit limits:

- graph node count,
- tensor rank,
- tensor dimensions,
- metadata byte size,
- pass iteration count,
- recursion depth,
- artifact size,
- cache size,
- compile time.

### Keep Backend Decisions Explainable

Backend selection must be inspectable. HS-IR and runtime plans must show:

- assigned backend,
- reason for assignment,
- fallback decisions,
- unsupported operations,
- relevant error budget or resource constraints.

### Avoid Silent Semantics Changes

Optimization passes must preserve mathematical intent. Approximate or noisy
lowering must be explicitly requested or allowed by a declared error budget.

### Sandbox Plugins

Backend plugins must start as declarative manifests. Executable backend code must
be opt-in, versioned, signed or pinned where practical, and isolated from
validation paths.

## Security Gates For Changes

Any change that touches compiler inputs, IR, backend APIs, runtime plans,
generated artifacts, or CI must answer:

1. What is the trust boundary?
2. What input is attacker-controlled?
3. What invariants are validated before lowering?
4. What resource budgets apply?
5. Could this execute host code?
6. Could this write outside the intended workspace/cache?
7. Could this hide a backend fallback or wrong-code decision?
8. What negative tests were added?

## Testing Requirements

Required now:

- unit tests for validation and rejection paths,
- deterministic IR dump tests,
- malformed metadata tests,
- unsupported operation tests,
- CI with least privilege.

Required before native parser or serialized IR formats:

- property tests for schema validation,
- fuzz targets for parsers/deserializers,
- ASan/UBSan jobs for native code,
- corpus seed files for valid and invalid IR,
- crash and timeout triage process.

Required before release:

- dependency review,
- CodeQL/code scanning,
- SBOM or dependency inventory,
- provenance or artifact attestation,
- documented vulnerability reporting process.
