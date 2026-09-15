# Bounded Native I/O Plan

RFC 0313 extends the existing plan-driven native experiment with actual input
and output movement derived from the same checked graph.

```text
a[33,7], b[7,5] -> planned input I/O -> Matmul -> ReLU -> Sum
                                    -> planned output I/O -> y[33]
```

On CUDA, input I/O uploads 924 + 140 bytes and output I/O downloads 132 bytes.
On C11, the equivalent steps bind existing host buffers, without copying them.
Both targets still use exactly the previous generated kernels and FP32 oracle.

## Run

```sh
PYTHONPATH=.:src python3 examples/bounded_native_io.py
sh docker/native-io/operator.sh --c11
# Only on an explicitly reviewed idle sm86 GPU host:
sh docker/native-io/operator.sh --cuda-reviewed
```

The first command is pure verification, not execution. Operator runs are bounded
native containers and produce private evidence directories. To compare them:

```sh
PYTHONPATH=.:src python3 examples/bounded_native_io.py \
  --compare CPU_EVIDENCE/record.json GPU_EVIDENCE/record.json
```

## What This Does Not Claim

`device_global` identifies a separate address space, not a specific RAM technology.
The core physical memory kind remains `unknown`; no HBM claim is made. Explicit
copy byte counts are not measured latency, energy or total memory traffic.
These costs remain unknown. Initialization and driver-internal copies are excluded.

The new plan belongs to the closed native operator. The core partition planner
and ordinary trusted runtime are unchanged, and do not yet plan external I/O.
No arbitrary plans, native plugin loading or performance claims are introduced.
See [RFC 0313](../rfcs/0313-bounded-native-io-plan.md) for the exact contract.

## Validation Status

Implementation and malformed-plan tests are available. Actual native acceptance
is pending; no previous CPU/GPU observation is treated as evidence of this path.
