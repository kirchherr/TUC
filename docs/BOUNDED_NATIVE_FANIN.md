# Bounded Native Fan-In Candidate

Status: pure candidate verified; native workers prepared; native acceptance pending.

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

## Worker Preparation

[RFC 0318](../rfcs/0318-bounded-native-fanin-workers.md) defines the separate
native execution/security boundary. `docker/native-fanin/` contains C11 and sm86
CUDA workers, fixed plan tables, operand-specific readiness/copy checks and
25 compile-time fault variants per profile. Mixed profiles additionally omit
their required left/right operand transfer. Both inputs must be ready before
Matmul, and output publication is required. Producers run sequentially.

```bash
PYTHONPATH=.:src python examples/bounded_native_fanin_workers.py
PYTHONPATH=.:src pytest -q tests/test_bounded_native_fanin_workers.py
```

The default verifier is pure. The separate operator uses pinned, networkless,
read-only, unprivileged containers with explicit resource/time limits. A CPU-only
CI job runs C11, ASan/UBSan and bounded native contract mutation checks. The
operator's matrix mode requires a separately approved GPU host/run. Expected
observation dictionaries in tests are synthetic protocols, not native evidence.

## Still Pending

Native validation, security review, new dev001 transfer/run authorization,
actual six-profile same-image GPU observations and acceptance remain required.
No fan-in native evidence has been accepted. RFC 0317 fixtures and earlier
native evidence are unchanged. The [fanout proof](BOUNDED_NATIVE_FANOUT.md)
remains the latest accepted native experiment; general admission and performance
claims stay closed.
