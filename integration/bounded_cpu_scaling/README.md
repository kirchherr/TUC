# Installed bounded CPU scaling consumer

This standalone standard-library client declares its own six source graphs and
FP32 equations. It imports no TUC modules or other integration consumers. It
converts source through the installed `tuc-source-to-json` OCI parser and invokes
the installed `tuc-cpu-app inspect`, `run` and `run-batch` commands.

Default mode prints an inert candidate; `--emit` writes portable fixtures under
this directory's `tmp` folder. On supported Linux x86-64 with the intended wheel
and existing local Docker environment, copy this directory outside the checkout:

```sh
python3 -I consumer.py
python3 -I consumer.py --run
```

The fixed programs cover:

- Rank-one `[5]` and rank-two `[2,3]` inputs multiplied by a right-hand `[1]`
  tensor factor. Signed-zero outputs are checked by their FP32 bits.
- Calibrated classifiers: `X * gain[K] + offset[K]`, Linear with bias, then
  Softmax; shapes are `M=2,K=3,N=4` and `M=1,K=2,N=3`.
- Scaled attention arithmetic: `Q @ K.T`, multiply by `scale[1]`, row Softmax,
  then `P @ V`; shapes are `M=2,K=4,S=3,D=2` with scale `0.5`, and
  `M=1,K=2,S=4,D=3` with scale `0.75`. This does not implement masks, arbitrary
  attention APIs or model import.

Two datasets per graph produce 12 single runs and 58 output scalars. One
three-request classifier batch shares gain, offset, weights and bias and adds
24 scalars. The completed receipt checks six conversions, 12 single runs, one
batch with three requests, and 82 scalars: 22 scaler values bitwise and 60
composed values with `abs(actual-expected) <= 2e-6 + 2e-5*abs(expected)`.
Twelve visible classifier Softmax rows must be finite, positive and sum to one
within `8e-6`. Internal attention probabilities have no observed row-mass claim.

The oracle rounds each multiplication and ordered accumulation to FP32. For
Softmax it rounds `math.exp` to FP32 as an approximation to native `expf`; no
bitwise Softmax or universal libm accuracy claim is made. NumPy tests evaluate
the graph families separately from the consumer's scalar implementation.

Eight source/JSON controls reject literals, reversed broadcast operands, column
broadcasts, wrong widths and rank-zero tensors. Three numerical scaler controls
use finite normal inputs to produce overflow, a subnormal product and a nonzero
product rounded to zero. A fourth control overflows the last request of a
classifier batch after two numerically valid inputs. Each rejection requires
the exact closed diagnostic, empty stdout and workspace cleanup. Earlier batch
computations are not claimed to be rolled back.

All fixture bytes must remain unchanged. Successful records preserve source,
signature, graph, input, program, request and batch identities plus expected and
observed outputs. Only complete success creates `record.json`, exclusively.
Digests detect accidental mixing and do not authenticate evidence. Shared input
declarations do not imply resident native weights or performance gains.

Default/emit and unit tests provide no native execution evidence. Actual evidence
is pending an installed CI run. No CUDA, general broadcasting, scalar literals,
rank-zero inputs or performance claim is included.
