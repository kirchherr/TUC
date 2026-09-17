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

## Accepted Observations

Native execution passed on 2026-09-17. The static C11 baseline and each of the
three same-image matrix profiles completed ten cases plus replay: 726 scalar
checks, 554 rounding witnesses, 44 generated calls and 22 published outputs.
The matrix totals 2178 scalar checks, 77 CPU calls and 55 GPU calls.

| Observed completed work | cccc | gccc | gggg |
| --- | ---: | ---: | ---: |
| CPU / GPU calls | 44 / 0 | 33 / 11 | 0 / 44 |
| Upload calls / bytes | 0 / 0 | 22 / 11704 | 22 / 11704 |
| Download calls / bytes | 0 / 0 | 11 / 7260 | 22 / 2904 |
| Projection copy calls | 0 | 11 | 0 |
| Shared consumer calls | 22 | 22 | 22 |
| Published outputs | 22 | 22 | 22 |

The mixed profile actually completed eleven projection downloads for twenty-two
consumer calls, as planned. Twenty-one C11 and sixty-three matrix negative
controls reject. Missing projection download stops before either CPU consumer.
Invalidating shared availability after ReLU stops before the second consumer;
clobbering shared contents fails the numerical contract. Omitting only the
second publication fails despite all four operations completing. Nine static
schedule faults reject before native calls or allocation.

C11 ASan/UBSan passed. The sanitized native contract test accepted all three
schedules and rejected four invalid selectors plus all 8736 single-bit changes
to integer profile, buffer and event fields. This is deterministic bounded
mutation testing, not coverage-guided fuzzing or pointer/string corruption fuzzing.

The [comparison](../tests/golden/proofs/native_fanout_comparison.json) binds the
[C11 record](../tests/golden/proofs/native_fanout_c11_record.json) and
[matrix record](../tests/golden/proofs/native_fanout_matrix_record.json).
Twenty-one metadata-only evidence files contain the comparison, two records,
two preflight groups, twelve negative-control groups of at most eight entries,
two unknown-selector observations and two sanitizer observations. Existing
intake limits are unchanged. No raw tensors, device IDs, runtime handles or
host paths are serialized. CI executes C11 and revalidates recorded matrix
evidence; it does not execute on a GPU.

Observed source commit: `b226fa6d585b02362564f31023604e1160f75995`.
Transferred archive SHA-256:
`34899bfbcdce13d0e204606a9b0ebb602fef96391813a73636871fcc64ff7d28`.
The records bind the same fanout program and unchanged predecessor placement
program. These are same-maintainer observations, not independent reproduction
or hardware attestation. The reviewed host used driver 595.84 and Container
Toolkit 1.20.0, checked against the applicable
[driver](https://nvidia.custhelp.com/app/answers/detail/a_id/5821) and
[container](https://nvidia.custhelp.com/app/answers/detail/a_id/5850) advisories.
This is not a vulnerability-free or complete GPU-isolation claim. No experiment
containers remained running; GPU utilization/memory returned to baseline.

Prior evidence, core code/defaults and ordinary native admission remain unchanged.
Arbitrary inputs/programs/shapes, performance, independent reproduction and
cross-vendor claims remain open. See [RFC 0316](../rfcs/0316-bounded-native-fanout.md)
for the dedicated native-execution security boundary and exact scope.
The successor [bounded native fan-in](BOUNDED_NATIVE_FANIN.md) now completes
distinct producer placements and checked input availability under RFCs 0317/0318.
Required review of the combined fanout/fan-in integration remains open, as does
independent reproduction.
