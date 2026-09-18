# Installed bounded CPU application consumer

This standalone client imports the installed TUC package and the standard
library. It defines its own supported graphs and input data. Its default mode
prepares inert applications; native compilation and execution require explicit
commands. The [native CI run](https://github.com/kirchherr/TUC/actions/runs/35339997831)
passed on `c9ebb2675f5114b7332284ce5fa380e8f259bb43`; its original observed
record is retained in [observed-ci-c9ebb26.json](observed-ci-c9ebb26.json).

The two graphs are:

- `projection`: a `(2,3) @ (3,2)` Matmul followed by ReLU and a separate axis-one
  Sum of the raw projection; public outputs are `activated` and `totals`.
- `activation`: ReLU on a `(2,3)` tensor; the public output is `activated`.

The reference calculations use explicit binary32 rounding and application math,
independent of generated manifests or dispatch code.

## Run the installed client

Install the TUC wheel and its dependencies into a virtual environment, and copy
this directory outside the repository. Run from that copied directory with the
environment's Python. `-I` excludes the working directory and `PYTHONPATH` from
Python's module search.

```sh
python3 -I consumer.py
```

This prints the two program digests with `native_execution_observed: false`.
It does not call a compiler, Docker or a native loader.

On Linux x86-64 with an existing trusted Docker executable and a usable local
`unix:///var/run/docker.sock`, explicitly build and execute:

```sh
python3 -I consumer.py --run
```

The public runtime builds a fixed static application for each graph, runs three
input cases twice, compares the results with the independent reference and
closes each handle. The required totals are 12 successful runs and 72 scalar
comparisons. A projection with finite inputs that overflow during multiplication
must additionally return the runtime reason `numeric_rejection`. A successful
command reports one such rejection. The linked CI run passed these requirements;
they remain mandatory for each new execution.

The runtime uses private temporary workspaces and executes by immutable image
ID. It selects the fixed local endpoint and trusted CLI path with a fresh empty
Docker configuration per invocation. User Docker contexts, credentials and
arbitrary commands are not parameters. See the
[application guide](../../docs/BOUNDED_CPU_APPLICATION.md) for a complete custom
graph example, platform prerequisites and error handling.

## Exercise the native parser

Generate the two fixed parser-test contexts without native execution:

```sh
python3 -I consumer.py --emit-fuzz
```

Each private `tmp/application-<graph>-...` directory contains the prepared
application, the fixed harness, input/output seed files and an identity record.
The expected response is derived from the Python reference and is synthetic
until compared with native output.

The explicit sanitizer operator regenerates those contexts, builds the pinned
ASan/UBSan test images and runs both the process-function corpus and the actual
stdin/EOF application wrapper:

```sh
sh fuzz_operator.sh --fuzz
```

The corpus requires exactly 1,368 cases for projection and 1,092 for activation.
It covers all request truncations, 1–64 extra bytes, every single-bit mutation,
special FP32 words, all undersized response capacities and null arguments.
Canary bytes verify that responses stop at their declared size. The wrapper
must match the independent success bytes exactly and return exit two with no
stdout for truncated, oversized and wrong-program frames. Request-digest
mutations deliberately test native opaque echo; only the host decoder verifies
the request hash. Digests do not authenticate a native process.

The sanitizer operator is a fixed conformance tool separate from the public
runtime handle. It retains its generated contexts and Docker test image for
inspection; the public runtime's context-manager cleanup does not own these
operator artifacts.

## CI and scope

[The workflow](../../.github/workflows/bounded-cpu-application.yml) installs a
fresh wheel outside the checkout, verifies package origin, runs the static
application client and sanitizer corpus, then retains a record binding observed
results to program digests, harness hashes, wheel SHA-256 and source commit.
The linked run passed 333 Linux tests, all 12 application calls, 72 comparisons,
one overflow rejection and all 2,460 sanitizer parser cases. The retained JSON
is the original CI record, not a synthetic unit-test receipt. Its source and
wheel hashes describe that specific run; subsequent revisions require their
own verification.

This slice supports only the bounded static FP32 CPU subset. It adds no CUDA
execution, general runtime admission, dynamic shape support, autograd, arbitrary
kernel input or performance claim. Earlier frozen conformance sources and
evidence remain separate. See [RFC 0324](../../rfcs/0324-bounded-cpu-application.md)
for the protocol and runtime security contract.
