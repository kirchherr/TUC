# Bounded Plan-to-Native Bridge

RFC 0311 executed the right kernels but the operator named their sequence by
hand. This experiment derives that sequence and its operand bindings from the
existing compiler's checked HAC-IR and backend assignments.

```text
restricted source -> HAC-IR -> capability plan -> checked dispatch table
                                               -> C11 / physical CUDA
```

The two targets share identical HAC-IR, kernels, input corpus and numerical
contract. They have different backend assignments and different intermediate
buffer bindings. Each native worker follows the generated three-row table.
Invalid opcodes, order, target or buffer edges fail before generated calls.

## Run

```sh
PYTHONPATH=.:src python3 examples/bounded_plan_native_bridge.py
sh docker/plan-native-bridge/operator.sh --c11
# Only on an explicitly reviewed idle sm86 GPU host:
sh docker/plan-native-bridge/operator.sh --cuda-reviewed
```

The first command is pure verification. The operator commands run reviewed
native binaries in bounded containers. Compare their private evidence directories:

```sh
PYTHONPATH=.:src python3 examples/bounded_plan_native_bridge.py \
  --compare CPU_EVIDENCE/record.json GPU_EVIDENCE/record.json
```

## What Remains Open

This is AOT lowering of one closed core-plan slice, not a general native runtime.
The normal trusted executor deliberately rejects the experiment backends.
The operator still owns external input/output copies; the current core transfer
plan does not include their cost. GPU memory uses `unknown`, not a false HBM
claim. Target selection offers one fixed capability per run; mixed native
placement and performance are not tested here.

See [RFC 0312](../rfcs/0312-bounded-plan-native-bridge.md) for the limits, security
exception and exact acceptance criteria.

## Observed Result

On 2026-09-15 native Linux x86_64 C11 and physical RTX 3060 sm86 CUDA both
passed the unchanged ten cases plus replay: 33 generated calls, 363 scalar
checks and 256 nontrivially rounded outputs per target. All twelve controls
were rejected on each target. The five schedule faults produced zero generated
calls and zero reported tensor bytes. C11 ASan/UBSan and CUDA SASS policy checks
passed. The two accepted records bind identical HAC-IR and distinct dispatch
headers, including opposite intermediate-buffer bindings.

Observed source commit: `6debc53fb49efb378d60eaf08d40d954ec24af85`.
Transferred archive SHA-256:
`104e832d97243b0e0ca1625ae7a40e23d736597320cab3639f7dc9101638a883`.
The acceptance commit changes no observed program file.

Accepted evidence in `tests/golden/proofs/`: `plan_native_comparison.json`,
two `plan_native_TARGET_record.json` files, two preflights, a C11 sanitizer
observation, and twenty-four target-specific rejections. The shared numerical
observation schema is unchanged; only these new program/image-bound records
support the plan-driven claim. Old records do not acquire new meaning.

The reviewed host still used driver 595.84 and Container Toolkit 1.20.0, with
no compute processes before or after the runs. GPU memory returned to the
87 MiB baseline; no experiment container remained. No unrelated workload or
service was modified. The driver review is the dated
[RFC 0311 host review](BOUNDED_COMPOSED_CHAIN.md#observations); the
[toolkit bulletin](https://nvidia.custhelp.com/app/answers/detail/a_id/5850)
was checked again on 2026-09-15. These checks are not a security guarantee.

Independent reproduction remains outstanding. The next integration gap is
explicit external I/O transfer accounting, with a reviewed memory-domain model,
not general native execution or a performance claim.

## Integration Queue

On 2026-09-15, PRs #100 through #107 remain open. The full CI, native C11 and
Security workflows of #107 passed. The first PR, #100, targets `main` and is
blocked by a required approving review with write access, not by failed tests.
Do not bypass that rule. Merge reviewed predecessors in order, retargeting each
successor to `main` after its predecessor merges. Native development does not
constitute that independent approval.
