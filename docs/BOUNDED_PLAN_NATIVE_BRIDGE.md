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
exception and exact acceptance criteria. Native observations are pending.

## Integration Queue

On 2026-09-15, PRs #100 through #107 remain open. The full CI, native C11 and
Security workflows of #107 passed. The first PR, #100, targets `main` and is
blocked by a required approving review with write access, not by failed tests.
Do not bypass that rule. Merge reviewed predecessors in order, retargeting each
successor to `main` after its predecessor merges. Native development does not
constitute that independent approval.
