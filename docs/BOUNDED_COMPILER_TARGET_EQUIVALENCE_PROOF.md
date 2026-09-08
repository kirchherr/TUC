# Bounded Compiler Target Equivalence Proof

## Status

Accepted under RFC 0303 after deterministic C11 emission, a zero-call
preflight, controlled static `x86_64` execution, independent reference
comparison, and aggregate CUDA/SASS-versus-C11 validation passed.

Decision: `rfcs/0303-bounded-compiler-target-equivalence-proof.md`.

Threat model:
[Bounded Compiler-Emitted C11 Threat Model](BOUNDED_COMPILER_EMITTED_C11_THREAT_MODEL.md).

## Research Question

RFC 0302 proved that one accepted Source Intent payload can produce code that
runs on one physical GPU. This proof asks a more hardware-neutral question:

> Can the exact same admitted compute intent and public workload be lowered
> through a separately specified non-CUDA target, execute without device
> access, and preserve the same terminal reference semantics?

```text
one accepted Source Intent + one fixed public workload
  |-> deterministic CUDA emission -> sm_86 SASS -> physical GPU -> PASS
  `-> deterministic C11 emission  -> static x86_64 ELF -> host -> PASS
                     aggregate input/provenance checks -> PASS
```

This is deliberately a two-target feasibility result. It is not a universal
hardware proof and does not establish that arbitrary programs or ISAs are
portable.

## Non-CUDA Target

Run deterministic C11 emission inspection without Docker or device access:

```bash
python3 examples/bounded_compiler_emitted_c11_emission.py
```

The emitter accepts only the canonical float32 `[4, 8] x [8, 2]`
Matmul-plus-ReLU Source Intent and workload already used by RFC 0302. It emits
a metadata-only plan, a fixed workload header, and exactly two C11 functions.
Tests require all checked-in artifacts under `docker/c11-observation/` to equal
fresh emission byte for byte.

The generated translation unit contains the two function definitions. The
separate harness owns process-boundary checks, a fixed public test vector, and
a separately implemented reference calculation. No caller-controlled text is
interpolated into code, symbols, compiler arguments, or commands.

## Controlled Procedure

Build the pinned GCC builder and static `scratch` runtime image:

```bash
docker compose --profile compiler-emitted-c11 \
  build --pull compiler-emitted-c11
```

Run the zero-call preflight:

```bash
python3 examples/bounded_compiler_emitted_c11_proof.py --preflight
```

Acceptance requires the exact image configuration and Compose security
contract, `NOT_EXECUTED`, zero generated-function calls, zero workload bytes,
no device or CUDA access, and a passing process-security boundary.

Run the fixed workload:

```bash
python3 examples/bounded_compiler_emitted_c11_proof.py --execute
```

Execution calls exactly two generated functions, uses a 256-byte stack working
set, and records PASS only if finite float32 terminal output matches the
independent reference within `1e-5`. No timing is collected.

## Aggregate Proof

Validate both accepted observations and emit the metadata-only aggregate:

```bash
python3 examples/bounded_compiler_target_equivalence_proof.py
```

The aggregate rejects either child report unless its own closed validator
passes. It then requires identical Source Intent payload and file digests,
identical workload payload and file digests, identical workload semantics, and
reference correctness on both targets. Target-specific facts remain outside
Source Intent.

## Evidence Contract

The C11 observation uses the closed schema
`schemas/bounded_compiler_emitted_c11_observation_report.v0.schema.json` and
the accepted report
`tests/golden/proofs/bounded_compiler_emitted_c11_observation_report.json`.

The cross-target aggregate uses
`schemas/bounded_compiler_target_equivalence_proof.v0.schema.json` and
`tests/golden/proofs/bounded_compiler_target_equivalence_proof.json`.

Both reports bind reviewed inputs, generated-artifact plans, build and runtime
contracts, image identities, and sanitized observations by SHA-256. They omit
source text, generated source, raw tensor values, timing samples, commands,
host paths, environment values, and hardware identifiers.

## Interpretation

A PASS strengthens TUC's central feasibility argument: one neutral compute
intent can retain its reference semantics across two materially different
compiler targets and execution mechanisms, one CUDA-dependent and one without
CUDA or device access.

It does not prove arbitrary-program portability, cross-ISA portability,
cross-vendor accelerator execution, a general CPU or CUDA backend, native
performance parity, production admission, universal hardware support, vendor
replacement, or independent reproduction. Both accepted observations are
owned by the same maintainer, and the normal TUC executor and native/device
admission gates remain unchanged.
