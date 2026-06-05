# HAC-IR Dialect Contract

HAC-IR is TUC's hardware-agnostic compute layer. The current implementation is
still Python-level IR, but it now has an explicit v0 dialect contract that maps
toward a future native MLIR `tuc_hac` dialect.

## Version

```text
hac-ir.v0
```

The future MLIR dialect spelling is:

```text
tuc_hac.v0
```

The Python contract lives in `tuc.ir.dialect`.

## MVP Operations

The v0 operation family is deliberately small:

| Operation kind | Future MLIR op | Input arity | Output arity | Tensor budget | Linearity |
| --- | --- | ---: | ---: | ---: | --- |
| `matmul` | `tuc_hac.matmul` | 2 | 1 | 16 | `linear` |
| `elementwise` | `tuc_hac.elementwise` | 1-16 | 1-16 | 16 | `nonlinear` |
| `reduction` | `tuc_hac.reduction` | 1-16 | 1 | 16 | `linear` |
| `softmax` | `tuc_hac.softmax` | 1 | 1 | 16 | `nonlinear` |

The contract is derived from the MVP kernels rather than from a universal
hardware abstraction. New operation families should be added through RFCs and
tests.

## Required Compiler Attributes

Every HAC-IR v0 operation must carry these compiler-produced attributes:

| Attribute | Contract |
| --- | --- |
| `tuc.arithmetic_intensity` | finite non-negative number |
| `tuc.arithmetic_ops` | non-negative integer |
| `tuc.bytes_read` | non-negative integer |
| `tuc.bytes_written` | non-negative integer |
| `tuc.layout` | known `LayoutKind` |
| `tuc.layout_tile_shape` | tuple of positive integers, or empty tuple |
| `tuc.linearity` | operation-specific `linear` or `nonlinear` |
| `tuc.movement_notes` | tuple of non-empty strings |
| `tuc.preferred_memory_domain` | known `MemoryDomainKind` |
| `tuc.semantic_op` | must match the operation kind |
| `tuc.source_stage` | must be `tlir` |

Optional compiler attributes are:

- `tuc.layout_alignment_bytes`
- `tuc.max_error_budget`
- `tuc.operation_name`

Unknown `tuc.*` attributes are rejected in HAC-IR v0. HS-IR-specific attributes,
such as backend assignments, must not appear before HAC-IR validation completes.

## User Hints

The current frontend can still carry non-namespaced user hints such as:

- `max_error_budget`
- `prefer_analog_linear`
- `prefer_sparsity`
- `robust_to_noise`

Known hints are type-checked by the contract validator. Frontend code must
continue to reject caller-supplied reserved `tuc.*` attributes.

## Security Rules

The HAC-IR dialect contract is declarative validation only:

- It does not read files.
- It does not import user modules.
- It does not execute backend code.
- It does not spawn subprocesses.
- It does not load plugins or dynamic libraries.

The compiler validates HAC-IR immediately after TLIR lowering and again before
HAC-IR to HS-IR lowering. Unsupported operation shapes, invalid dialect
versions, malformed compiler attributes, and premature backend-assignment
metadata fail closed.

## Native MLIR Follow-Up

Before native MLIR or C++ dialect code accepts external input, TUC must add:

- TableGen/ODS definitions that mirror this contract.
- Parser and deserializer fuzz targets.
- ASan/UBSan sanitizer coverage.
- Resource limits for serialized MLIR input.
- Negative tests for malicious attributes and oversized artifacts.
