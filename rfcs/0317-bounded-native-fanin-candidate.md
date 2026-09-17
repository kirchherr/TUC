# RFC 0317: Bounded Native Fan-In Candidate

Status: Implemented as a pure candidate; native implementation and acceptance
completed separately in [RFC 0318](0318-bounded-native-fanin-workers.md).

## Decision

Prepare the next source/shape/numerical contract after RFC 0316 without extending
native execution admission. Two independent ReLU producers feed the two distinct
operands of a Matmul join, followed by an axis-1 Sum and one required publication.
Existing source intake, typed placement overrides and residency planning suffice.
No core/compiler/backend API changes are needed.

```python
left = tl.where(a > 0, a, 0)
right = tl.where(b > 0, b, 0)
projection = tl.dot(left, right)
row_sum = tl.sum(projection, axis=1)
tl.store(y, row_sum)
```

Shapes: a/left [33,7], b/right [7,5], projection [33,5], row_sum/y [33]; float32
throughout. Only this source intent is admitted for candidate verification.
Profile characters describe left ReLU, right ReLU, Matmul and Sum, in order:
cccc, gccc, cgcc, gcgg, cggg, gggg. Mixed profiles exercise either producer as the
remote operand at a CPU or GPU join. These six are not all sixteen placements.
No asynchronous/concurrent producer execution is implied by independent dataflow.

## Plan Contract

All profiles preserve identical HAC-IR. Backend choices and transfer decisions
remain in HS-IR and the partition/residency plans. At the join, both produced
operands must be available in the join's logical address space. Availability of
the raw input is not availability of its produced ReLU result. Operand identity,
order, shape, dtype, space and bytes must match the fixed graph. Missing either
producer, missing a required operand copy, an early join, operand substitution,
duplicate publication and absent publication fail metadata validation.

The data-only checker replays readiness, not tensor computations or hardware
events. Serialized candidate snapshots must match a freshly reconstructed plan
exactly; a checker result alone is not a native execution receipt.

Bounds: four operations, six logical tensors, at most nine buffer slots and ten
events. Maximum planned buffer bytes: 4768. Existing 64 KiB file and 512-item
metadata budgets remain unchanged; plans are kept in separate bounded files.
No aliases, mutation, allocator reuse, persistent buffers or runtime plan parser.

## Numerical Contract

The exact reference is sum over k,c of max(a[row,k],0)*max(b[k,c],0), evaluated
over exact binary32 inputs in rational arithmetic. ReLU introduces no rounding
for finite binary32 inputs. The ordered oracle uses separate binary32 products
and sequential additions with ties-to-even, no FMA contraction or reassociation.
The inherited conservative depth 1+7+5 gives gamma_13 times the exact nonnegative
row sum as an absolute-error budget. Signed zeros compare numerically only.
Fixed-corpus intermediate checks exclude underflow/overflow.

The ten-case corpus derives from the existing FP32 corpus, replacing its
mixed-sign case with a first case containing signs in both operands. A planned
replay yields 363 scalar checks per profile and 265 oracle rounding witnesses.
All 33 first-case results distinguish each of six wrong expressions: bypass
left, bypass right, bypass both, ReLU after Matmul, ReLU after Sum, missing join.
These are Python oracle checks, not observed native rejection controls.

## Security Boundary

This stage adds only repository-owned Python candidate verification and JSON
fixtures. Source is parsed as data, never imported/executed. There is no process
launch, native code emission, dynamic library, plugin discovery, device access,
network access, or caller-selected path in the CLI. Metadata budgets are checked
before reconstruction; unknown profiles, malformed shapes/dtypes, nonfinite
values, non-binary32 inputs and unsupported numeric magnitudes reject.

There is deliberately no --execute, --accept, worker or image-ID interface.
The candidate report explicitly records native_execution_observed=false and
normal_runtime_admission=false. It cannot substitute for RFC 0316 evidence.
Earlier accepted records and their program bindings remain untouched.

## Required Next Stage

The requirements below were fulfilled by RFC 0318 on 2026-09-17. Its
[acceptance report](../docs/BOUNDED_NATIVE_FANIN.md) records the actual native
observations; this RFC and its candidate fixtures remain planning evidence.

Native work requires a separately reviewed implementation of both producer
kernels, operand-specific readiness/copy guards, fixed C11/CUDA schedules and
observation validation. Update this RFC or add a dedicated execution RFC with
the exact worker threat model, resource limits and container isolation before
execution. Bind a source commit and archive, obtain authorization for any new
source transfer/host run, and review applicable driver/toolkit advisories.

Require C11 and all six same-image matrix profiles, ordered-policy and exact
reference checks, completed producer/join/copy/publication counters, replay,
missing-either-input controls, wrong-code controls, ASan/UBSan and bounded native
contract mutation tests. An earlier fanout approval does not authorize this new
payload. Performance, independent reproduction, arbitrary inputs/programs,
dynamic shapes and ordinary native runtime admission remain blocked.
