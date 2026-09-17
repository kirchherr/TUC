# Bounded Native Fan-In

Status: bounded C11 and six same-image physical CPU/GPU profiles passed on
2026-09-17. Ordinary native admission remains closed.

This experiment joins two separately placed ReLU producers at a Matmul,
then reduces and publishes one row-sum output. Source, shapes and numerical
meaning are fixed by [RFC 0317](../rfcs/0317-bounded-native-fanin-candidate.md).
The existing frontend/compiler/residency planner is unchanged.

```text
a [33,7] -> ReLU -> left  --+
                           +-> Matmul -> Sum(axis=1) -> row_sum [33]
b  [7,5] -> ReLU -> right --+
```

## Placements

Characters denote left ReLU, right ReLU, Matmul and Sum, respectively. Each
mixed profile has two distinct producer placements; the join must wait for both
produced operands in its address space. Observed worker counters match these
logical plans. Byte counts are not measured memory consumption or performance.

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

## Native Workers

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

## Accepted Observations

After exact-source transfer/run approval, C11 and all six profiles passed on
dev001 (RTX 3060, sm86). Each profile completed ten corpus cases plus replay,
363 scalar checks, 265 rounding witnesses, 44 generated calls, eleven calls to
each producer, eleven joins and eleven publications. The matrix totals 2178
checks, 1590 rounding witnesses, 132 CPU calls and 132 GPU calls. Its logical
copy counters total 62876 bytes. All four mixed profiles completed eleven
required produced-operand copies, covering both operands at CPU and GPU joins.

All 179 fault controls rejected with the required exit status and exact metadata:
25 C11, 150 matrix and four mixed operand-copy controls. Both unknown-profile
invocations also rejected. C11 baseline ASan/UBSan and all 16032 single-bit
contract-field mutation probes passed without relaxing host security settings.
No experiment containers remained; GPU use returned to 0%/87 MiB and existing
services remained running.

Thirty-seven new bounded metadata-only files under `tests/golden/proofs/`
retain actual operator records, preflights, grouped fault receipts and sanitizer
reports. `native_fanin_comparison.json` binds the two validated execution records.
The separate comparison module does not change the executed worker payload.

```bash
PYTHONPATH=.:src python examples/bounded_native_fanin_equivalence.py \
  tests/golden/proofs/native_fanin_c11_record.json \
  tests/golden/proofs/native_fanin_matrix_record.json
PYTHONPATH=.:src pytest -q tests/test_bounded_native_fanin_equivalence.py
```

These are same-maintainer operator receipts, not independent reproduction or
cryptographic execution attestation. The pure comparison checks bound metadata;
it cannot itself establish where arbitrary submitted receipts were produced.
RFC 0317 candidate fixtures and all earlier evidence remain unchanged. Fixed
inputs, source, shapes and sequential producers do not establish general runtime
admission, concurrent scheduling, arbitrary-input correctness or performance.

## Provenance And Security Review

Executed source commit: `4d996e68f1fb9630f3c9bef9e5be67b683120209`.

| Binding | SHA-256 |
| --- | --- |
| Source archive | `0a540a7b68258ca572fca043ec3d1d57d695613d4499606619c4fbd9872031be` |
| Program files | `f0d99127099be1a8688f8c3e4d577cecfb18bf6af20501677eac3c9e31dd15a5` |
| C11 operator image | `daf265207ba8974df0d4346260b5bf28331b6b4b82792f70b5324d0e22851b43` |
| Matrix operator image | `b7b8ecdb1330c44e262d3553009363f1e9bffe5df0fbfea3352701b61ac77057` |
| C11 sanitizer image | `1eb681a9986d9967ebfb2e17dbff062c4738616bbd39c3c5f818097914b91ef8` |

The archive digest was checked before extraction into a new private directory;
pure artifact reconstruction and the program digest matched before execution.
Python 3.12.3/NumPy 2.4.4 from the existing TUC verifier environment performed
metadata checks; no host packages were installed. Docker 29.7.0, Linux
7.0.0-28-generic, AppArmor and built-in seccomp remained in place.

The 2026-09-17 review checked NVIDIA's
[published bulletin index](https://github.com/NVIDIA/product-security/tree/main/2026).
Host driver 595.84 is above the Linux R595 fixed version 595.71.05 in the
[May driver bulletin](https://nvidia.custhelp.com/app/answers/detail/a_id/5821).
Container Toolkit/libnvidia-container 1.20.0 is above the fixed version 1.19.1 in
the [June toolkit bulletin](https://nvidia.custhelp.com/app/answers/detail/a_id/5850).
The inherited CUDA 12.8.1 image is not claimed current or vulnerability-free:
the [January CUDA bulletin](https://nvidia.custhelp.com/app/answers/detail/a_id/5755)
lists Nsight recipe, installer and Windows tooling issues. This Linux operator
does not invoke those Nsight paths or installers. That is a scope assessment,
not a full image vulnerability scan. GPU containers still share the host driver
and kernel; this remains a bounded research exception, not hostile-code isolation.
