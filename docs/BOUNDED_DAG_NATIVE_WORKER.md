# Shared Native DAG Worker

This successor to the [artifact compiler](BOUNDED_DAG_COMPILER.md) runs a fixed
portfolio through one event worker. Per-graph wrappers select generated
primitives; a shared validator and scheduler handle buffers, copies, execution
and output publication. The four families and three shapes produce twelve
graphs and 36 CPU/GPU placement plans. No family-specific arithmetic is added.

```text
typed HAC-IR + partition
        -> bounded DAG compiler
        -> C11/CUDA kernels + manifest
        -> revalidated compiled descriptors and dispatch wrappers
        -> shared native validator -> isolated fixed worker
        -> exact, context-bound observation checks
```

The ordinary runtime remains closed. This worker accepts only a reviewed plan
index and preflight/execute mode, using compiled inputs and independently
derived reference bits. It does not accept arbitrary graphs or tensors.
See [RFC 0320](../rfcs/0320-bounded-dag-native-worker.md) for invariants, numerical
scope, isolation, budgets and the physical-run approval boundary.

## Preparation and validation

```sh
python examples/bounded_dag_native.py
pytest -q tests/test_bounded_dag_native.py
```

The default command is inert. Its expected matrix totals are 216 runs,
468 CPU calls, 504 GPU calls, 4,212 terminal comparisons and 324 publications.
Planned transfers total 94,152 bytes. GPU result-domain validation separately
accounts for 504 diagnostic downloads totaling 95,400 bytes. These are expected
counts, not measurements or observations.

On an appropriate Linux x86-64 Docker host, the CPU-only command is:

```sh
sh docker/bounded-dag-native/operator.sh --c11
```

It runs twelve static and sanitized profiles with their exact controls, plus
194,688 sanitizer-backed plan-field mutation checks. The dedicated CPU workflow
retains its verified record. Candidate reports and synthetic unit-test receipts
cannot establish an executed process; consult the commit-bound CI record.

## GPU preparation

The `--matrix` operator mode is implemented for a separately approved sm86 host.
All 36 profiles use one image, including all-CPU profiles. Each GPU operation
and planned transfer completes before dependent reads. Owned storage is reset
between replays; skipped producers/copies, corrupted values and missing outputs
must reject with exact partial counters. Timeouts, crashes and device errors
cannot substitute for successful fault controls.

Before any dev001 connection or transfer, bind the committed source/archive,
review current driver/toolkit advisories and obtain fresh explicit authorization
for the concrete payload. The current implementation and CPU-only workflow do
not constitute physical GPU acceptance. Earlier fan-in/fanout observations
retain their original source bindings and do not cover this worker.
