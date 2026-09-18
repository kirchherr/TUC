# Installed application C11 conformance

This standalone client uses only public installed TUC APIs and Python's standard
library. It compiles the same bounded application as `bounded_dag_compiler`, then
emits a fixed CPU context with independent FP32 input and reference constants.
The Python program never launches or loads generated code.

Use the dedicated [workflow](../../.github/workflows/bounded-source-c11.yml) for
the complete isolated installation and execution procedure. It runs outside the
checkout with Python `-I`. For equivalent manual preparation, install the reviewed
wheel into a separate virtual environment, copy this directory outside the
checkout, and write the exact wheel's SHA-256 as one `sha256:<64 lowercase hex>`
line to `wheel-sha256.txt` in that copy. Keep the wheel environment on `PATH`.

```sh
# Pure candidate report; requires the prepared wheel digest sidecar.
python3 -I consumer.py

# Emit a fresh private context under this client's tmp/ directory.
python3 -I consumer.py --emit

# Explicit native CPU test route; requires Linux x86-64 and Docker.
# Builds/runs only the closed application and its fixed fault variants.
sh operator.sh --c11

# Pure revalidation of a completed context and its captured receipts.
python3 -I consumer.py --accept tmp/bounded-source-c11.<suffix>
```

The operator prints the evidence directory. `record.json` is written only after
both baseline executions, all thirteen fault variants in both builds, invalid
argument controls and accept-time source/context checks succeed. Expected receipt
values in unit tests are synthetic protocol fixtures and are not observations.

Three fixed corpora and two replays give six runs per baseline, 42 primitive
calls, 36 scalar comparisons and twelve public-output checks. The CPU plan owns
eleven slots totaling 336 bytes and has no transfers. All nonzero intermediate
values must be finite normal binary32; signed zeros compare numerically equal.

This proves a fixed installed application route when the workflow passes. It
does not accept new runtime inputs, execute CUDA, contact dev001, register a
native runtime, benchmark hardware or authenticate third-party evidence.
