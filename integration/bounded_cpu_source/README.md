# Installed source-to-JSON-to-CPU consumer

This standalone standard-library client owns six small source programs, their
signatures and numeric inputs, and an independent ordered binary32 reference.
It imports no TUC modules. The installed `tuc-source-to-json` console converts
source text into a bounded `source_intent.v0` graph; the separate `tuc-cpu-app`
console then inspects and executes that graph. The source text is never imported
as a Python module or evaluated as a Triton kernel.

Copy this directory outside the checkout after installing the wheel into a
virtual environment. Use that environment's Python:

```sh
# Inert descriptions and source/signature/input fixtures; no native processes.
python3 -I consumer.py
python3 -I consumer.py --emit

# Explicit isolated parser and CPU execution on Linux x86-64 with local Docker.
python3 -I consumer.py --run
```

The corpus contains fanout, true fanin and ReLU/Sum, each in two shape profiles.
Six source conversions feed twelve CPU calls with changing inputs and 56 scalar
comparisons. Every converted graph is compared with the client's independent
graph expectation before being passed to the CPU console. Public bindings,
program identity across inspect/run, independently recomputed request digests,
and source/signature/graph/input hashes are checked and recorded. Program
digests are observed compiler identities; this client does not reimplement
the compiler's nine-file program hash calculation.

Ten negative controls cover foreign imports, eval, file and network expressions,
malformed syntax, excessive and boolean dimensions, a mismatched kernel name,
unsupported softmax and nonterminal returns. Rejections require empty stdout
and exact closed diagnostics. Original fixture bytes must remain unchanged;
each parser/runtime invocation must leave its private workspace empty. A host
file-effect marker must remain absent. These are bounded conformance checks,
not a general sandbox or arbitrary Triton compatibility claim.

`record.json` is created exclusively after every check succeeds. Default and
fixture reports are inert expectations, not native evidence. Native observation
remains pending until the installed workflow has completed successfully.

## Small application example

[projection.py.txt](projection.py.txt) is source data. Its separate
[signature](projection-signature.json) describes every positional argument,
including the store destination. [Inputs](projection-inputs.json) contain only
the external input arrays:

```sh
set -e
mkdir -m 700 work
tuc-source-to-json projection.py.txt --signature projection-signature.json --workspace work > graph.json
tuc-cpu-app inspect graph.json
tuc-cpu-app run graph.json --inputs projection-inputs.json --workspace work
```

Expected named output: `{"scores":[0.0,10.0]}`. Conversion is explicit and may
start an isolated parser container; `inspect` performs no native execution.
The accepted text uses literal Triton imports, one `@triton.jit` function and
the documented bounded tensor expressions. It does not admit arbitrary Python,
general pointer programs, CUDA execution or a default parser/runtime backend.
