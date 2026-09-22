# Installed bounded CPU Softmax consumer

This standalone standard-library client imports no TUC modules or other clients.
It declares six fixed source graphs, converts their source with the installed
`tuc-source-to-json` OCI parser, and invokes installed `tuc-cpu-app inspect`, `run`
and `run-batch`. Default mode prints an inert candidate; `--emit` writes portable
fixtures under this directory's `tmp` folder. Neither mode invokes a console.

On supported Linux x86-64 with the intended wheel installed and the existing
local Docker environment, copy this directory outside the checkout and run:

```sh
python3 -I consumer.py
python3 -I consumer.py --run
```

The fixed graph families are:

- Softmax alone: inputs `[2,1]` and `[3,7]`.
- Linear plus bias plus Softmax: `X[2,3], W[4,3]` and `X[1,2], W[3,2]`.
- Attention arithmetic `Q @ K.T -> Softmax -> P @ V`: `M=2,K=3,S=4,D=2`
  and `M=1,K=2,S=3,D=3`. This is a small fixed arithmetic graph, without masks,
  scaling, general attention APIs or model-import claims.

Two datasets per graph produce 12 single executions and 82 output scalars. One
classifier batch has three different inputs and shared weight/bias declarations,
adding 24 scalars. The receipt therefore checks six conversions, 12 single runs,
one batch with three requests, and 106 scalars. Shared JSON inputs do not imply
resident native weights or a performance improvement.

The independent scalar reference rounds products, sequential sums, Softmax shifts
and divisions to FP32. It uses `math.exp` rounded to FP32 as an approximation to
the native `expf`; it makes no bitwise or universal libm accuracy claim. Observed
outputs must satisfy `abs(actual-expected) <= 2e-6 + 2e-5*abs(expected)`.
The 22 visible Softmax rows must have positive finite entries and row sums within
`8e-6` of one. The internal probability matrix in the attention graph is not a
public output, so its observed row mass is not claimed.

Eight source/JSON controls reject unsupported axes, rank, nested expressions,
an import-call attempt and incompatible semantic attributes. Four numerical
controls supply valid finite normal FP32 inputs that produce subtraction overflow,
a subnormal exponential, a zero exponential, or a subnormal shift. Each runtime
control must return the exact numeric-rejection diagnostic with empty stdout.

All commands and filenames are fixed, output and time are bounded, every original
fixture must remain unchanged, and each workspace must be empty after success or
rejection. Only a complete successful check creates `record.json`, exclusively.
The receipt binds source, signature, graph, input, program, request and batch
identities and preserves expected and observed outputs. These hashes detect
accidental mixing and do not authenticate evidence.

[Installed CI run 35694760750](https://github.com/kirchherr/TUC/actions/runs/35694760750)
passed all counts above at `a69b5fb`; its
[original receipt](../../docs/evidence/bounded-cpu-softmax-35694760750.json) is retained.
Unit tests use a separate ordered NumPy FP32 oracle and synthetic response
mutations; they are not native execution evidence. No CUDA, performance, general
runtime admission or broad Triton compatibility is claimed.
