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

Actual native C11 and physical sm86 CUDA runs passed on 2026-09-15. Each target
completed ten cases plus replay, 33 generated calls and 363 scalar checks under
the unchanged FP32 contract. C11 also passed ASan/UBSan.

| Completed boundary work | C11 | CUDA |
| --- | ---: | ---: |
| Host bindings | 33 | 0 |
| Upload calls / bytes | 0 / 0 | 22 / 11704 |
| Download calls / bytes | 0 / 0 | 11 / 1452 |
| Total completed I/O steps | 33 | 33 |

All twenty negative controls per target were rejected. The twelve static
compute/I/O table faults fail before generated calls or copies. The skipped
output control runs all three kernels but fails completion: CUDA reports only
two uploads and no download. The seven numerical wrong-code controls also fail.

Accepted metadata: [comparison](../tests/golden/proofs/native_io_comparison.json),
[C11 record](../tests/golden/proofs/native_io_c11_record.json), and
[CUDA record](../tests/golden/proofs/native_io_cuda_record.json). The 46 accepted
artifacts also include both preflights, C11 sanitizer execution and forty
rejections. They contain no raw tensor values, runtime handles or device IDs.
The dedicated CI job executes C11 and revalidates recorded CUDA evidence; it
does not execute on a GPU.

The observed source commit was `5136451be9f902fd5f71114bc5de1948e2a0ec01`.
The transferred source archive SHA-256 was
`6946cd41218ddadd3048cceeddeb6280a1fb1ab11d1b648244af33064b636593`.
Both records bind the same new program-files digest and the unchanged previous
bridge program. These are same-maintainer observations, not independent
reproduction or hardware attestation. Prior proof records were not relabeled.

Next research question: can shared core boundary-residency planning support a
bounded mixed native placement while preserving this explicit completion
contract? That is not established by the present all-C11 / all-CUDA comparison.
