# Bounded Native Fan-In Candidate

Status: pure candidate verified; no native execution or accepted native evidence.

The next experiment joins two separately placed ReLU producers at a Matmul,
then reduces and publishes one row-sum output. Source, shapes and numerical
meaning are fixed by [RFC 0317](../rfcs/0317-bounded-native-fanin-candidate.md).
The existing frontend/compiler/residency planner is unchanged.

```text
a [33,7] -> ReLU -> left  --+
                           +-> Matmul -> Sum(axis=1) -> row_sum [33]
b  [7,5] -> ReLU -> right --+
```

## Planned Placements

Characters denote left ReLU, right ReLU, Matmul and Sum, respectively. Each
mixed profile has two distinct producer placements; the join must wait for both
produced operands in its address space. These are logical plans, not observed
work, memory consumption measurements or performance results.

| Profile | Join | Remote produced operand | Copy bytes/run | Buffer bytes |
| --- | --- | --- | ---: | ---: |
| cccc | CPU | none | 0 | 2920 |
| gccc | CPU | left | 1848 | 4768 |
| cgcc | CPU | right | 280 | 3200 |
| gcgg | GPU | right | 1196 | 4116 |
| cggg | GPU | left | 1196 | 4116 |
| gggg | GPU | none | 1196 | 4116 |

Copy bytes include external inputs and terminal output movement. In gggg no
produced join operand crosses spaces; external uploads and output download still
occur in the plan. Six selected profiles are not a complete placement search.

## Verification

```bash
PYTHONPATH=.:src python examples/bounded_native_fanin.py
PYTHONPATH=.:src pytest -q tests/test_bounded_native_fanin.py
```

Nine deterministic JSON fixtures in `tests/golden/native_fanin_candidate/`
bind the source intent, numerical contract, six plans and candidate report.
Every plan retains HAC-IR, HS-IR, partition/decision dumps and typed overrides.
The candidate report records no native observation and cannot grant admission.

The rational reference and ordered FP32 oracle verify the fixed ten-case corpus
plus a planned replay: 363 values/profile and 265 rounding witnesses. Six
wrong expressions each differ beyond the budget in all 33 first-case outputs.
The tests also reject missing producers/copies, early joins, substituted or
swapped operands, malformed buffers, changed snapshots and publication faults.

## Still Pending

Native producer kernels, a reviewed operator/worker, sandboxing and fault
controls, native sanitizers, actual C11/GPU observations and acceptance remain
required. No new source was transferred and no native worker was run for this
candidate. The [fanout proof](BOUNDED_NATIVE_FANOUT.md) remains the latest
accepted native experiment. General admission and performance claims stay closed.
