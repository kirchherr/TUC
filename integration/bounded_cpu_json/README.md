# Installed CPU JSON CLI consumer

This standalone standard-library client owns its graph JSON, numeric inputs
and independent binary32 references. It invokes the installed `tuc-cpu-app`
console outside the TUC checkout. The six programs combine fanout, true fanin
and ReLU/Sum with two small shape profiles. Two input corpora per program
require 12 native calls and 56 scalar comparisons.

Copy this directory into a separate application directory after installing
the wheel into a virtual environment. Use that environment's Python:

```sh
# Inert description and fixture generation; no native processes.
python3 -I consumer.py
python3 -I consumer.py --emit

# Explicit native CLI conformance on Linux x86-64 with existing local Docker.
python3 -I consumer.py --run
```

Successful conformance additionally requires a checked numeric overflow
rejection and six negative graph/input controls: duplicate keys, malformed
JSON and symlink files. Every normal call verifies graph/input bytes remain
unchanged and the private runtime workspace is empty after cleanup. A result
is written to `record.json` only after all checks pass. Default reports and
expected values are not native observations.

The separate hand-written [projection.json](projection.json) and
[projection-inputs.json](projection-inputs.json) are a small starting example:

```sh
tuc-cpu-app inspect projection.json
mkdir -m 700 work
tuc-cpu-app run projection.json --inputs projection-inputs.json --workspace work
```

Expected outputs are `{"scores":[0.0,10.0]}`. See the
[CLI guide](../../docs/BOUNDED_CPU_JSON_CLI.md) for the file/numeric contracts.

The [workflow](../../.github/workflows/bounded-cpu-json-cli.yml) builds and
installs an offline wheel, checks the installed import origin, exercises the
console, and wraps the original consumer record with source, wheel and consumer
hashes in `ci-record.json`.
The runtime and native parser sanitizer conformance remain in their existing
independent workflows.

Native conformance was observed in successful [push CI run 35343784690](
https://github.com/kirchherr/TUC/actions/runs/35343784690) on source revision
`1b2a1ce4d8db86de320af341dd5f44ada916aa79`. Its installed CLI ran outside the
checkout: six programs, 12 successful calls, 56 scalar comparisons, one checked
numeric rejection and six negative controls passed. Input files remained
unchanged and runtime workspaces were clean. The job also passed 308 tests in
8.84 seconds. The [original observation](observed-ci-1b2a1ce.json) retains that
executed source identity; it is not evidence for later revisions. Owner review
and final CI remain required.
