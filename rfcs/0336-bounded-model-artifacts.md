# RFC 0336: Capability-Planned Bounded Model Artifacts

- Status: Implemented candidate
- Date: 2026-10-01
- Scope: Data-only model compilation

## Decision

Add `tuc.compiler.bounded_model_artifacts` as a narrow facade from the existing
bounded fixed-parameter model into the existing capability-planned Source Intent
artifact compiler. The API emits inspectable C11/CUDA source artifacts and
planner evidence while keeping fixed parameters separate from variable inputs.

This advances the reusable model from a CPU application format to a neutral
compiler input. It does not compile source, execute a runtime, access a device,
discover a backend, or grant native admission.

## Contract

`compile_bounded_model_artifacts(model_data, backend_bindings)` first revalidates
the complete model bytes through RFC 0333. It then reconstructs Source Intent
from the canonical graph and invokes RFC 0321 with one or two explicit bounded
capability bindings.

The result binds:

- the existing model digest;
- the Source Intent and backend-binding digests;
- every generated artifact file by SHA-256;
- fixed FP32 parameters at their artifact tensor indices;
- the remaining variable input bindings; and
- explicit public output bindings.

The resulting model-compilation digest changes with parameter bits, graph,
capabilities, placement, I/O bindings, or generated artifacts. Changing only
parameters preserves the graph program sources while changing both model and
model-compilation identity.

`validate_bounded_model_artifacts` recompiles from the original model and
capabilities, invokes RFC 0321's deep revalidator, and rejects wrapper, planner,
binding, metadata, or artifact drift with one closed diagnostic.

## Security Boundary

Model input remains bounded JSON bytes. Backend bindings remain exact typed,
data-only capability records. No path, module, import hook, plugin, environment,
network, subprocess, dynamic library, compiler invocation, device access, or
generated-code execution is accepted. Returned source text is inert and does
not confer execution authority.

## Acceptance

- fixed and variable inputs cover the complete generated-artifact input set;
- parameter extents match their exact tensor shapes and preserve FP32 bits;
- capability order is canonical while capability changes affect identity;
- CPU, CUDA, and mixed plans use the existing no-fallback planner contract;
- changed parameters retain graph artifacts but change model binding identity;
- all result fields survive deterministic deep revalidation; and
- hostile model data and returned-result drift fail closed.

## Non-Claims

This RFC establishes no native execution, CUDA compatibility, resident weights,
performance, dynamic shapes, arbitrary models, backend plugin execution, device
discovery, or independent organizational reproduction.
