# Observed Shared DAG Native Equivalence

The source-bound RFC 0320 worker passed its complete, explicitly authorized
physical matrix on 2026-09-18. Twelve fixed family/shape graphs each ran with
CPU-only, GPU-only and alternating placement through one shared scheduler and
one CUDA image. The unchanged RFC 0319 compiler supplies the same primitive
sources across placements. This is observed fixed-corpus correctness evidence.

## Observed results

Each profile group contains twelve plans, three input vectors and two replays.
The counts below include only successful baseline execution receipts; preflights
and deliberately failing controls are counted separately.

| Counter | CPU | GPU | Mixed | Total |
| --- | ---: | ---: | ---: | ---: |
| Case runs | 72 | 72 | 72 | 216 |
| CPU primitive calls | 324 | 0 | 144 | 468 |
| GPU primitive calls | 0 | 324 | 180 | 504 |
| Terminal scalar checks | 1,404 | 1,404 | 1,404 | 4,212 |
| Output publications | 108 | 108 | 108 | 324 |
| Planned upload calls | 0 | 162 | 198 | 360 |
| Planned upload bytes | 0 | 29,472 | 38,400 | 67,872 |
| Planned download calls | 0 | 108 | 126 | 234 |
| Planned download bytes | 0 | 5,616 | 20,664 | 26,280 |
| Validation-only download calls | 0 | 324 | 180 | 504 |
| Validation-only download bytes | 0 | 56,952 | 38,448 | 95,400 |

All 36 preflights passed with zero computation counters. All 132 fault controls
rejected with their exact reason and partial counters: 36 missing producers,
36 corrupted outputs, 36 omitted publications and 24 missing required copies.
Both invalid invocations rejected before computation. The operator exited zero;
timeouts, crashes or device errors were not accepted as negative controls.

The separate [CPU CI run](https://github.com/kirchherr/TUC/actions/runs/35318832060)
provides static and ASan/UBSan baselines. Each completed 72 runs, 324 calls,
1,404 scalar checks and 108 publications, with all 72 fault controls and four
invalid invocations. Its sanitizer-backed contract test accepted 36 canonical
plans and rejected 194,688 single-bit plan mutations. Every matrix CPU baseline
matches both CPU CI builds, except the explicit worker identity field.
Both runs remain same-maintainer evidence; the CI host is a separate environment,
not independent third-party reproduction.

## Source and provenance binding

| Binding | Value |
| --- | --- |
| Executed source commit | `cdb67d59c27f712606da1117e98870cc1f53692d` |
| Source archive bytes | `16568320` |
| Source archive SHA-256 | `7b167332d93a3ef6c31311cd85478a65a8acf120f3ab7c67a97889487162bcfe` |
| Reconstructed context | `sha256:36b396f46ba9d092ec8dc20d22d5e1ba8d8704a9b87370fcdef886f404b83e88` |
| Matrix Docker image identity | `sha256:8e0e38d4708955b59fdc7ef4cdaee015b0ac061a890eae9e300ab0bb9c4521db` |
| Matrix record file SHA-256 | `c7cac5ecddd47c6726af12c83026bba581b136516bb408e94ae822dbb5a501dc` |
| CPU CI record file SHA-256 | `598039c13b310b9eb4b3659292686f73470f422c88a0db5a72958e1609d337ec` |
| CPU CI artifact | `10536611051` in run `35318832060` |
| CPU CI ZIP SHA-256 | `925067e790b946f376c8a918231e7b247ebedf52b58310993594ae1e14a19d56` |

The user approved the concrete commit/archive before connection and transfer.
Archive bytes were checked before extraction; reconstructed context bytes were
checked before building. After execution, all 320 context/evidence files were
retrieved into an exclusive local directory. Local acceptance reconstructed the
full context, required every exact receipt and matched the remote aggregate
record byte-for-byte in canonical content. The table's record hashes cover the
original downloaded file bytes, including their final newline.

The two original aggregate records are retained unchanged under
`tests/golden/proofs/bounded_dag_native_c11_record.json` and
`tests/golden/proofs/bounded_dag_native_matrix_record.json`. They contain all
125 CPU and 206 matrix receipts, including controls. The separate pure
`examples/bounded_dag_native_equivalence.py` validates both records and compares
observed profile totals. It does not compile, load, execute or authorize code.
Later verifier/documentation commits do not change the executed source binding.

Revalidate the retained metadata without executing native code:

```sh
python examples/bounded_dag_native_equivalence.py \
  tests/golden/proofs/bounded_dag_native_c11_record.json \
  tests/golden/proofs/bounded_dag_native_matrix_record.json
pytest -q tests/test_bounded_dag_native_equivalence.py
```

The comparison's record digests use canonical JSON. They intentionally differ
from raw file hashes, which retain original serialization and its final newline.

## Environment and review

The physical host reported Linux `7.0.0-28-generic` x86-64, one NVIDIA GeForce
RTX 3060 (compute capability 8.6), driver `595.84`, Container Toolkit and
libnvidia-container `1.20.0`, and Docker `29.7.0`. Builtin seccomp, AppArmor and
cgroup namespaces were available. Preparation/acceptance reused Python `3.12.3`
and NumPy `2.4.4`. No dependency or host setting was changed.

The approved operator enforced the RFC's non-root, read-only, no-network,
no-mount, dropped-capability/no-new-privileges and resource/time limits. Builds
used the committed pinned image/frontend digests, offline build steps and
strict binary inspection. sm86 SASS was present, PTX absent and FMA instructions
absent in the proof image. NVCC emitted non-blocking unused-variable warnings
for fault-only bookkeeping fields in excluded compile-time variants; the
executed source was preserved rather than changed to suppress diagnostics.

The 2026-09-18 advisory review used NVIDIA's
[GPU bulletin 5821](https://nvidia.custhelp.com/app/answers/detail/a_id/5821)
(Linux R595 fixed threshold `595.71.05`) and
[Container Toolkit bulletin 5850](https://nvidia.custhelp.com/app/answers/detail/a_id/5850)
(CVE-2026-24260 fixed in `1.19.1`). The observed versions exceed these thresholds.
The [official 2026 index](https://github.com/NVIDIA/product-security/blob/main/2026/README.md)
showed no newer relevant driver/toolkit bulletin at review time. This is a
dated, scoped advisory review, not a complete vulnerability attestation for
the host or container images. GPU containers share the host kernel and driver.

## Scope and remaining work

This acceptance covers only the reviewed four families, three shapes, fixed
normal-or-zero FP32 corpus and three placement patterns per graph. The pure
candidate continues to say `native_execution_observed=false`; only actual
records describe execution. Reference-bit comparisons treat signed zeros as
equal and do not establish a numerical contract for arbitrary inputs.

Ordinary runtime admission remains false. No dynamic shapes, arbitrary source
or tensor inputs, parallel scheduling, additional ISA/vendor, independent
reproduction, latency, energy or performance claim follows from these receipts.
Older fan-in/fanout evidence retains its original bindings. Any changed dev001
payload still requires a fresh reviewed source/archive and explicit approval.
