# Native MLIR Design Spike

TUC now includes a first native-MLIR-oriented design spike for the HAC-IR layer.

## Artifact

The spike lives at:

```text
examples/mlir/tuc_hac_ir_spike.mlir
```

It is parseable with MLIR's generic unregistered dialect path:

```bash
python scripts/verify_mlir_spike.py
```

or directly:

```bash
mlir-opt --allow-unregistered-dialect examples/mlir/tuc_hac_ir_spike.mlir
```

## What It Shows

The artifact sketches a future `tuc_hac` dialect shape for:

- `tuc_hac.matmul`
- `tuc_hac.elementwise`
- Tensor type flow.
- Movement metadata.
- Preferred memory domain metadata.
- Layout metadata.
- Error budget metadata.

This mirrors the current Python HAC-IR contract without introducing native code.

## Non-Goals

This spike does not add:

- A C++ MLIR dialect.
- A TableGen dialect definition.
- Native parsers or deserializers.
- MLIR passes.
- Backend code generation.
- Runtime execution.

Those are later steps and require fuzzing, sanitizer coverage, and a stronger
native-code threat model before accepting untrusted inputs.

## Security Rules

For now, the MLIR artifact is repository-owned design text:

- It is not loaded by the compiler pipeline.
- It does not execute backend code.
- It does not introduce device access.
- It does not add dynamic library loading.
- It is verified only by `mlir-opt --allow-unregistered-dialect` in the Docker
  development environment.

The first real native MLIR implementation should keep the same compiler
boundary discipline: validate before lowering, keep text dumps deterministic,
and add fuzz targets before accepting external serialized IR.
