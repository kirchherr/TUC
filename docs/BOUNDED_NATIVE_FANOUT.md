# Bounded Native Fanout

RFC 0316 adds a fixed branch to the native source experiment. One Matmul result
feeds ReLU and a direct row Sum; a second Sum reduces the ReLU output. Both
33-element outputs must be published and verified. The exact input corpus and
reviewed C11/CUDA arithmetic primitives are unchanged.

| Profile | Matmul | ReLU | Raw Sum | Positive Sum | Copy bytes / run |
| --- | --- | --- | --- | --- | ---: |
| cccc | CPU | CPU | CPU | CPU | 0 |
| gccc | GPU | CPU | CPU | CPU | 1724 |
| gggg | GPU | GPU | GPU | GPU | 1328 |

In gccc the two CPU consumers use the same host projection slot. The planner
has two inter-operation edges but emits only one 660-byte projection download,
in addition to 1064 bytes of input upload. Copy reuse is scoped to an immutable
value within one invocation, not aliasing, allocation reuse or persistent cache.
These logical counts are not measured bandwidth, latency or a speed ranking.

## Reproduce

```sh
PYTHONPATH=.:src python3 examples/bounded_native_fanout.py
sh docker/native-fanout/operator.sh --c11
# Explicitly reviewed idle sm86 host only:
sh docker/native-fanout/operator.sh --matrix-reviewed
PYTHONPATH=.:src python3 examples/bounded_native_fanout.py \
  --compare CPU_EVIDENCE/record.json MATRIX_EVIDENCE/record.json
```

Verification is pure. The explicit operator builds one matrix image for three
fixed profiles, with fresh bounded containers and no runtime compilation or
plan parsing. This is not the full sixteen-placement matrix for four operations.

## Status

Native observations are pending. Require 726 scalar checks, 554 non-exact
rounding witnesses, 44 calls and both publications per profile across ten cases
plus replay. The shared placement must complete eleven projection downloads
for twenty-two consumer calls. Missing second publication, invalidated shared
availability, clobbered shared contents, wrong consumer edges and wrong output
bindings are explicit negative controls, alongside the numerical controls.

C11 ASan/UBSan and native contract integer-field mutation checks are mandatory.
Prior evidence, core code/defaults and ordinary native admission remain unchanged.
Arbitrary inputs/programs/shapes, performance, independent reproduction and
cross-vendor claims remain open. See [RFC 0316](../rfcs/0316-bounded-native-fanout.md)
for the dedicated native-execution security boundary and exact scope.
