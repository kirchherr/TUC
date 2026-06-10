# Backend API v0.1

TUC's Backend API v0.1 is a prototype authoring contract for external backend
experiments. It is not a plugin ABI and it does not auto-discover or execute
third-party code.

The goal is narrow:

```text
Describe what a backend can accept as declarative data, let the compiler create
an inspectable HS-IR plan, and allow a trusted in-process prototype backend to
lower only the graph it explicitly supports.
```

## Current Surface

The v0.1 surface is:

- `BackendCapability`
- `Backend` protocol
- `LoweringResult`
- Schema-versioned backend capability manifests.
- Schema-versioned transfer-cost profile manifests.
- Explicit backend capability registry.
- HAC-IR and HS-IR dialect contracts.
- Trusted Runtime Backend Executor Contract for fixed in-process execution.

Capability schema assumptions for error budgets, latency, energy, calibration,
and noise modeling are documented in
[Backend Capability Schema](BACKEND_CAPABILITY_SCHEMA.md).

The code lives in:

- `tuc.backends.base`
- `tuc.backends.registry`
- `tuc.manifests`
- `tuc.ir.dialect`
- `tuc.runtime.executor`
- `tuc.runtime.plan`
- `tuc.runtime.partitioning`

## What Backend Authors Provide

Backend authors should start with a capability description, not executable
plugin code.

```json
{
  "schema_version": "tuc.backend_capability.v0",
  "name": "linear-sim",
  "supported_ops": ["matmul"],
  "supports_noise_model": true,
  "supports_calibration": false,
  "preferred_for": ["matmul"],
  "max_error_budget": 0.05,
  "memory_domain": "analog_weight_bank",
  "supported_layouts": ["row_major"],
  "produced_layouts": ["row_major"]
}
```

Specialized accelerator-like capabilities use the same declarative surface:

```json
{
  "schema_version": "tuc.backend_capability.v0",
  "name": "systolic-sim",
  "supported_ops": ["matmul"],
  "supports_noise_model": false,
  "supports_calibration": false,
  "preferred_for": ["matmul"],
  "memory_domain": "device_sram",
  "supported_layouts": ["row_major"],
  "produced_layouts": ["blocked"]
}
```

This manifest is declarative. Loading it must not import backend modules, touch
devices, open network connections, or execute vendor tools.

Capability manifests can be collected through `BackendRegistry`:

```python
from tuc.backends.registry import BackendRegistry

registry = BackendRegistry.from_manifest_paths(
    ["examples/manifests/linear_sim_backend.json"]
)
```

The registry receives explicit file paths only. It does not scan directories,
resolve entry points, import backend modules, or store backend objects.

The registry can also explain pure-data support decisions:

```python
diagnostics = registry.diagnose_operation_support(operation)
```

These diagnostics are suitable for compiler review, backend author feedback, and
future partitioning reports because they state why a backend accepted or
rejected an operation without executing backend code.

## Capability Fields

| Field | Meaning |
| --- | --- |
| `name` | Stable backend name used in diagnostics and HS-IR assignments. |
| `supported_ops` | Operation families this backend can accept. |
| `preferred_for` | Operation families this backend should be preferred for when valid. |
| `supports_noise_model` | Whether the backend can model numeric or physical noise. |
| `supports_calibration` | Whether calibration is supported or expected. |
| `max_error_budget` | Maximum accepted operation error budget. |
| `memory_domain` | Where outputs reside after execution. |
| `supported_layouts` | Layouts accepted as inputs. |
| `produced_layouts` | Layouts this backend may produce. |

Valid operation families currently are:

- `matmul`
- `elementwise`
- `reduction`
- `softmax`

Valid memory domains and layouts are defined by `MemoryDomainKind` and
`LayoutKind` in `tuc.ir.memory`.

`max_error_budget`, `supports_noise_model`, and `supports_calibration` are
capability claims and planning assumptions. They are not correctness proofs,
hardware certificates, or permission to hide backend-specific behavior inside
HAC-IR. Transfer latency and energy assumptions belong to transfer-cost
profiles, not backend capability manifests.

## Layout Contract

`supported_layouts` and `produced_layouts` are separate on purpose.

A backend may accept one layout and produce another. TUC records that decision
in HS-IR as `tuc.produced_layout` and in runtime plans as layout-conversion
costs. Backend authors must not hide layout conversion inside backend-specific
lowering without making it visible to TUC.

## IR Contracts

Backends consume graph objects that have already passed compiler validation.
The current contracts are:

- [HAC-IR dialect contract](HAC_IR_DIALECT.md)
- [HS-IR dialect contract](HS_IR_DIALECT.md)
- [Runtime Executor trusted backend contract](RUNTIME_EXECUTOR.md)

HAC-IR describes hardware-agnostic compute intent and movement facts. HS-IR
describes backend assignment, produced layout, and runtime-transfer summaries.

Backend authors should treat unknown operations and unsupported layouts as hard
rejections. They should not silently emulate operations unless the capability
contract says the backend supports them.

## Minimal In-Process Backend

Prototype backends implement the `Backend` protocol:

```python
from __future__ import annotations

from tuc.backends.base import BackendCapability, LoweringResult
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import ComputeGraph, OperationKind


class MinimalLinearBackend:
    def __init__(self) -> None:
        self._capability = BackendCapability(
            name="minimal-linear",
            supported_ops=frozenset({OperationKind.MATMUL}),
            preferred_for=frozenset({OperationKind.MATMUL}),
            memory_domain=MemoryDomainKind.ANALOG_WEIGHT_BANK,
        )

    @property
    def capability(self) -> BackendCapability:
        return self._capability

    def lower(self, graph: ComputeGraph) -> LoweringResult:
        unsupported = [
            operation.name
            for operation in graph.operations
            if not self.capability.supports(operation)
        ]
        if unsupported:
            raise ValueError("backend cannot lower: " + ", ".join(unsupported))

        return LoweringResult(
            backend_name=self.capability.name,
            graph_name=graph.name,
            artifact="# backend-specific artifact placeholder",
            diagnostics=("lowered=prototype",),
        )
```

The runnable reference is `examples/backend_api_v0.py`.

The external-style author path is:

```text
examples/external_backend_author_path.py
```

It demonstrates the intended review flow for a toy backend author:

1. Provide a schema-versioned manifest.
2. Pass Manifest Claim Review for that explicit manifest path.
3. Load it through `BackendRegistry.from_manifest_paths(...)`.
4. Compile a graph using capability data only.
5. Run `assert_backend_conformance(...)`.
6. Lower only the HAC-IR subgraph assigned to the explicitly constructed
   trusted backend object.
7. Emit claim-review and conformance reports as deterministic review
   artifact.

## Transfer-Cost Profiles

Backends or experiments may also provide transfer-cost profile manifests:

```json
{
  "schema_version": "tuc.transfer_cost_profile.v0",
  "name": "example_profile",
  "fallback": {
    "bandwidth_gb_s": 16.0,
    "base_latency_ns": 20000.0,
    "energy_pj_per_byte": 100.0
  },
  "edges": [
    {
      "source_domain": "analog_weight_bank",
      "target_domain": "gpu_hbm",
      "bandwidth_gb_s": 128.0,
      "base_latency_ns": 2500.0,
      "energy_pj_per_byte": 12.0
    }
  ]
}
```

These profiles affect planning and diagnostics only. They are not proof of real
hardware performance.

## Security Rules

Backend API v0.1 follows these rules:

- Capability checks are pure data checks.
- Manifest loading is bounded, schema-versioned, duplicate-key rejecting, and
  unknown-field rejecting.
- Backend capability manifests must not contain import paths, plugin modules,
  shell commands, device paths, or dynamic-library names.
- TUC does not auto-discover backends.
- Backend registries are explicit capability registries, not executable plugin
  registries.
- Backend support diagnostics must be pure data and must not include host paths,
  device identifiers, imported module names, or backend execution output.
- TUC does not execute backend code while parsing, validating, dumping IR, or
  selecting capabilities.
- Backend lowering may run only for explicitly constructed trusted backend
  objects inside the current process.
- Runtime execution may run only through trusted executor contracts that keep
  external artifacts, device access, dynamic loading, subprocesses, JIT, and
  network access forbidden.
- Backend lowering must validate `capability.supports(operation)` before
  emitting artifacts.
- Backend artifacts are data until a later RFC defines an execution sandbox.

## Author Checklist

Before proposing a backend:

- Document supported operations and numeric semantics.
- Document accepted and produced layouts.
- Document memory domain and transfer assumptions.
- Document error-budget, latency, energy, noise-model, and calibration
  assumptions using [Backend Capability Schema](BACKEND_CAPABILITY_SCHEMA.md).
- Provide a capability manifest and negative tests.
- Show deterministic diagnostics for rejected operations.
- Do not add plugin discovery, imports, subprocesses, dynamic loading, device
  access, or artifact execution without a new security RFC.

Backend proposals should also follow the dedicated
[Backend Author Certification](BACKEND_AUTHOR_CERTIFICATION.md) checklist and
copy the executable negative-test template from
`tests/test_backend_author_negative_template.py`.

Prototype backends should also run the reusable
[Backend Conformance Fixtures](BACKEND_CONFORMANCE.md) through
`assert_backend_conformance`.

Backend authors should store or attach the deterministic conformance report
artifact produced by `dump_backend_conformance_report(...)` when asking
maintainers to review a prototype backend.

Backend authors should also review the invalid and misleading examples in
[Backend Capability Schema](BACKEND_CAPABILITY_SCHEMA.md) before proposing new
capability fields or manifests.

The executable test for the full author path is
`tests/test_external_backend_author_path.py`.

The systolic manifest path at `examples/systolic_manifest_path.py` demonstrates
that a specialized accelerator capability can be loaded as explicit manifest
data, planned by the compiler, checked by runtime readiness, and executed only
through an already trusted Runtime Executor backend.

Specialized accelerator manifests should also pass
[Manifest Claim Review](MANIFEST_CLAIM_REVIEW.md) before maintainers treat them
as acceptable planning evidence. The current report schema is
`schemas/manifest_claim_review_report.v0.schema.json`, and the runnable example
is `examples/manifest_claim_review.py`.

The external-style backend author path runs Manifest Claim Review before
registry loading and stops if the manifest is blocked.

## Current Limitations

Backend API v0.1 does not yet provide:

- Stable binary ABI.
- Plugin packaging.
- Auto-discovery.
- Backend plugin lifecycle management.
- Device enumeration.
- Artifact execution.
- Sandboxing.
- Backend certification.
- Native MLIR lowering.

Those are later steps and must be added behind explicit threat models, fuzzing,
sanitizer coverage for native code, and least-privilege runtime controls.
