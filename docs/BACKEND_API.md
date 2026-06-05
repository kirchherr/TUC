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
- HAC-IR and HS-IR dialect contracts.

The code lives in:

- `tuc.backends.base`
- `tuc.manifests`
- `tuc.ir.dialect`
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

This manifest is declarative. Loading it must not import backend modules, touch
devices, open network connections, or execute vendor tools.

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
- TUC does not execute backend code while parsing, validating, dumping IR, or
  selecting capabilities.
- Backend lowering may run only for explicitly constructed trusted backend
  objects inside the current process.
- Backend lowering must validate `capability.supports(operation)` before
  emitting artifacts.
- Backend artifacts are data until a later RFC defines an execution sandbox.

## Author Checklist

Before proposing a backend:

- Document supported operations and numeric semantics.
- Document accepted and produced layouts.
- Document memory domain and transfer assumptions.
- Provide a capability manifest and negative tests.
- Show deterministic diagnostics for rejected operations.
- Do not add plugin discovery, imports, subprocesses, dynamic loading, device
  access, or artifact execution without a new security RFC.

## Current Limitations

Backend API v0.1 does not yet provide:

- Stable binary ABI.
- Plugin packaging.
- Auto-discovery.
- Device enumeration.
- Artifact execution.
- Sandboxing.
- Backend certification.
- Native MLIR lowering.

Those are later steps and must be added behind explicit threat models, fuzzing,
sanitizer coverage for native code, and least-privilege runtime controls.
