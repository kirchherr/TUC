# Bounded DAG Artifact Compiler

The compiler now lowers a bounded class of typed HAC-IR DAGs through one shared
API. Matmul, ReLU and row Sum kernels are derived from operation types and shapes;
the emitter does not recognize example names or fixed topologies. Target mapping
and the existing residency planner determine explicit memory movement and
bind/execute/publish events without putting hardware details in HAC-IR.

```python
from tuc.backends.bounded_dag import (
    DAGTarget, lower_bounded_dag, validate_bounded_dag_artifacts,
)

targets = {"selected_cpu": DAGTarget.C11, "selected_gpu": DAGTarget.CUDA_SM86}
artifacts = lower_bounded_dag(compiled.hac_ir, compiled.partition_plan, targets)
validate_bounded_dag_artifacts(
    artifacts, compiled.hac_ir, compiled.partition_plan, targets,
)
texts = artifacts.files()  # Five in-memory strings; no files or processes created.
```

The target keys must exactly match the backends used in the selected partition.
The returned files are `generated.h`, `generated.c`, `kernels.cuh`, `schedule.h`
and `manifest.json`. The manifest binds all four sources, HAC-IR, shapes, target
placements, explicit public return aliases, buffer slots, events and numerical
policy. Schedule symbols are integer-indexed. Revalidation rejects any changed
source or metadata; it does not execute or admit an artifact.

## Current limits

| Property | Accepted range |
| --- | --- |
| Operations | 1-8; rank-two Matmul, rank-one/two ReLU, axis-one Sum |
| Tensors | At most 24, static float32, dense row-major, dimensions 1-64 |
| Residency | At most 48 buffers and 96 events; 256 KiB planned storage |
| Arithmetic | At most 1,000,000 scalar steps, ordered binary32 arithmetic |
| Metadata / artifacts | 64 KiB / 256 KiB |
| Native admission | Closed; primitives need a separately validated caller |

Native callers must validate live pointer extents, distinct output storage,
launch geometry and numerical environment. Finite normal values or zero are
required at every rounded intermediate. Rounding is nearest-even, contraction
and flushing are disabled; signed zeros compare numerically equal. The emitted
primitives do not establish arbitrary-input correctness or an error bound.

## Reproduce the inert portfolio

With the project environment installed, run:

```sh
python examples/bounded_dag_compiler.py
python examples/bounded_dag_c11.py
pytest -q tests/test_bounded_dag.py tests/test_bounded_dag_codegen.py tests/test_bounded_dag_c11.py
```

The first command reports 36 bundles: four graph families, three shapes, and
all-CPU, all-GPU and mixed placement. The seven-operation case includes two
Matmul joins, a reused projection, three external inputs and two terminal outputs.
Tests explore every placement of four graphs and compare 504 buffer-schedule
replays against independent original-graph arithmetic. They also exercise
invalid metadata, shape/SSA/budget violations, public returns, source tampering
and agreement between the schedule header and manifest.

## Fixed C11 conformance

[RFC 0319](../rfcs/0319-bounded-dag-artifact-compiler.md) defines a separate,
isolated CPU-only route for twelve fixed family/shape cases. On a suitable Linux
x86-64 Docker host, its operator command is:

```sh
sh docker/bounded-dag-c11/operator.sh --c11
```

The command creates an exclusive context under `tmp/`, builds pinned static and
sanitized workers, runs them with resource and access restrictions, verifies
their bounded receipts and writes `record.json` into that context. Each build
must pass 1,404 scalar comparisons and reject twelve cases for each of three
fault variants. The dedicated GitHub Actions workflow retains only the verified
metadata record. A candidate report or passing pure test does not establish
that native execution occurred; consult the actual commit-bound CI run.

CUDA execution, general runtime admission, concurrency, dynamic shapes and
performance remain unestablished. Existing fanout/fan-in observations retain
their original source bindings; they do not cover this new compiler.
