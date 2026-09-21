# Fixed Add/Bias C11 conformance

This standalone consumer uses the installed TUC wheel to emit four CPU graphs:
equal-shape vector Add, equal-shape matrix Add, right row-bias Add, and a
Matmul → bias → ReLU → residual Add → axis-1 Sum pipeline. Its scalar FP32
oracle is independent of the generated dispatch and schedules.

Use Linux x86-64 with an existing local Docker daemon. Copy this directory
outside the checkout, install the intended TUC wheel in the active Python
environment, and write that wheel's `sha256:<hex>` digest to
`wheel-sha256.txt`. Run:

```sh
python3 -I consumer.py
sh operator.sh --c11
```

The first command generates only a candidate report. The operator emits a
private bounded context, builds the pinned static and ASan/UBSan images,
executes the fixed controls in isolated containers, and validates the receipts
before writing `record.json` here. It does not execute CUDA or accept arbitrary
native input, compiler flags, commands, or images.

Each baseline performs 24 successful case runs, 136 entrypoint calls, 114 scalar
comparisons, 24 publications, 112 expected rejections, and 532 unchanged-output
sentinel checks. Rejections cover descriptor counts, extents, aliases, numeric
values and intermediates, and floating-point environment guards. These are
entrypoint boundary cases, not binary-frame parser fuzzing. Three checker fault
controls and one invalid invocation per build produce ten total observations.
Unexpected crashes or sanitizer failures never count as successful controls.

Receipt binding covers the wheel identifier, installed compiler sources,
consumer, generated artifacts, and fixed build/operator files. This prevents
accidental context mixing; it is not receipt authentication. Candidate generation
and pure protocol tests do not establish native execution or runtime admission.

[CI run 35349477030](https://github.com/kirchherr/TUC/actions/runs/35349477030)
executed all ten observations successfully at `f27e2c8`. The original
[combined receipt](../bounded_cpu_add_bias/observed-ci-f27e2c8.json) retains that
revision, wheel/consumer identities and actual static/sanitized observations.
