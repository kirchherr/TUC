# Bounded Source Intent consumer

`consumer.py` uses only the installed `tuc` package and Python's standard library.
It constructs one seven-operation Source Intent DAG: two independent matrix
projections, two ReLUs, a third matrix multiplication combining those branches,
and two row sums. Four public inputs produce two public returns, `branch_total`
and `joined_total`. The first return preserves the raw left projection's sum;
the second summarizes the recombined activation. This topology is separate from
the earlier chain, fan-out, fan-in and diamond artifact portfolio.

Three capability sets compile the same module. The CPU supports all operations;
the GPU-only profile does likewise. In the mixed profile, the GPU supports and
prefers matrix multiplication, while the CPU supports all operations and prefers
elementwise and reduction operations. The compiler selects placements without
operation overrides. The report includes those selection reasons, buffer slots,
copy events, execution events and public output publication.

Copy `consumer.py` and `expected_report.json` into a directory outside the TUC
checkout. With the built TUC wheel installed in that interpreter, run:

```sh
python -I consumer.py --check expected_report.json
```

The default invocation, `python -I consumer.py`, prints the same compact,
deterministic JSON. `--check` requires exact UTF-8 bytes from a regular file no
larger than 64 KiB. A mismatch exits with status 1 and emits no report. Report
contents include no local paths or elapsed time. Source Intent, HAC-IR, primitive
sources and return bindings must agree across profiles before output is produced.

This is a compiler and artifact inspection consumer. It neither compiles nor
executes native C/CUDA code, contacts a host, or claims device availability or
native numerical conformance. Its Python tests independently compare ordered
FP32 reference arithmetic with a metadata schedule simulation. That simulation
provides no evidence of native execution, runtime admission or performance.
