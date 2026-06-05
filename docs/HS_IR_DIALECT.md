# HS-IR Dialect Contract

HS-IR is TUC's hardware-specific compiler stage. It records backend choices and
runtime-relevant layout decisions after HAC-IR validation and partitioning.

## Version

```text
hs-ir.v0
```

The future MLIR dialect spelling is:

```text
tuc_hs.v0
```

The Python contract lives in `tuc.ir.dialect`.

## Operation Contracts

HS-IR keeps the MVP operation family from HAC-IR and adds backend-specific
placement facts:

| Operation kind | Future MLIR op | Input arity | Output arity | Tensor budget | Linearity |
| --- | --- | ---: | ---: | ---: | --- |
| `matmul` | `tuc_hs.matmul` | 2 | 1 | 16 | `linear` |
| `elementwise` | `tuc_hs.elementwise` | 1-16 | 1-16 | 16 | `nonlinear` |
| `reduction` | `tuc_hs.reduction` | 1-16 | 1 | 16 | `linear` |
| `softmax` | `tuc_hs.softmax` | 1 | 1 | 16 | `nonlinear` |

HS-IR operation contracts inherit HAC-IR movement and semantic attributes, but
`tuc.source_stage` must be `hac-ir`.

## Required HS-IR Attributes

Every HS-IR v0 operation must carry:

- All required HAC-IR movement and semantic attributes.
- `tuc.assigned_backend`: a bounded simple backend name.
- `tuc.produced_layout`: a known `LayoutKind` produced by that backend.

The assigned backend must match the module-level `backend_assignments` metadata.
Unknown `tuc.*` attributes are rejected.

## Graph Metadata

HS-IR v0 requires these graph metadata fields:

- `lowered_from = "hac-ir"`
- `backend_assignments`
- `movement_summary`
- `runtime_transfer_summary`

`backend_assignments` must have exactly one entry per operation and no extra
entries.

`movement_summary` must include:

- `arithmetic_intensity`
- `movement_model`
- `operation_count`
- `total_arithmetic_ops`
- `total_bytes_read`
- `total_bytes_written`

`runtime_transfer_summary` must include:

- `estimated_transfer_energy_pj`
- `estimated_transfer_latency_ns`
- `layout_conversion_count`
- `total_data_movement_bytes`
- `total_layout_conversion_bytes`
- `total_transfer_bytes`
- `transfer_edge_count`

All numeric totals must be finite, non-negative, and internally consistent:
`total_data_movement_bytes` must equal transfer bytes plus layout-conversion
bytes.

## Security Rules

The HS-IR contract is declarative validation only:

- It does not discover backends.
- It does not execute backend lowering.
- It does not load plugins or dynamic libraries.
- It does not read manifests or files.
- It does not repair mismatched assignments.

Wrong-stage metadata, malformed backend names, invalid produced layouts,
unsupported reserved compiler attributes, and inconsistent transfer summaries
fail closed.

## Follow-Up

Future HS-IR work should add contracts for concrete backend artifact manifests,
calibration requirements, runtime synchronization, and backend certification
metadata before accepting external backend implementations.
