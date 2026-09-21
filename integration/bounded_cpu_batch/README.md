# Installed bounded CPU batch consumer

This standard-library-only client calls the installed `tuc-cpu-app` console. It
declares its own SourceIntent JSON graphs and uses independent, ordered scalar
FP32 equations. It imports no TUC modules or other integration clients.

Default mode prints an inert candidate. `--emit` writes portable JSON fixtures
under this directory's `tmp` folder. On Linux x86-64, copy the folder outside the
checkout into an environment containing the intended TUC wheel and run:

```sh
python3 -I consumer.py
python3 -I consumer.py --run
```

`--run` requires the existing supported local Docker environment. It invokes
`inspect GRAPH.json` and `run-batch GRAPH.json --batch BATCH.json --workspace DIR`
through the console beside the current Python interpreter. All commands, paths
and deadlines are controlled by the client. No command is taken from JSON.

The six programs cover affine Linear, an eight-operation ReLU-gated MLP, a
rank-one elementwise product and rank-two repeated-operand squaring. Each model
family has two small shape profiles, and each batch has three changing inputs.
Linear and MLP weights are declared once in `shared_inputs`; the square graph
also covers an empty shared-input mapping. Product outputs preserve signed zero.

One extra affine batch changes request order, one request ID and one input.
Its unchanged request contents retain their request digests, while its batch
digest changes. Program identity stays fixed. Across the seven successful batch
invocations, the client checks 21 ordered results and 96 FP32 scalar values.

Six invalid batch controls cover a missing final input, duplicate IDs, overlapping
shared/request inputs, an incorrect extent, malformed JSON and 17 requests.
Two runtime numeric controls fail at the second or last request. Rejection must
produce the exact closed diagnostic, empty stdout and a clean workspace. The
client does not claim that earlier computations were undone. Dedicated CLI unit
tests cover validation before building and build lifecycle behavior; this receipt
does not measure build counts, resident weights or performance.

Every original graph and batch file must remain unchanged. Successful observations
record full public bindings, graph/batch/merged-input hashes, program/request/batch
identities, expected and observed outputs, and rejection controls. `record.json`
is created exclusively only after every check passes. Digests detect accidental
mixing; they do not authenticate evidence. Native execution remains pending until
an actual installed CI run supplies its original receipt.

Tests compare the scalar oracle with separately ordered NumPy FP32 equations and
exercise forged responses, signed zero, identity changes and inert fixture mode.
Synthetic test responses are not native execution evidence.
