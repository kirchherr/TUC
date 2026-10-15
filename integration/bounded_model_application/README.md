# Reproduce the bounded model application observation

This directory contains the fixed installed CPU consumer, a Python standard-
library auditor and the original CI observation. The consumer runs three model
contexts and four rejection controls. The auditor checks 18 exact FP32 results,
the fixed model identities and request/response integrity without importing TUC
or executing native code.

## Replay the retained observation

Copy `audit_native_receipt.py` and `observed-ci-59ad813.json` into an otherwise
empty directory. Python 3.11 or later is sufficient; no packages are required:

```sh
python -I -S audit_native_receipt.py --ci-packet observed-ci-59ad813.json
```

A successful report contains `status: PASS`, `scalar_checks: 18`,
`rejection_checks: 4`, `tuc_imported: false` and
`native_execution_performed: false`. The packet's recorded audit must match
the recomputed report exactly. Invalid fields, malformed hashes, context drift,
incorrect values and changed claims reject with `native_record_rejected`.

This checks the retained data and its arithmetic. It does not authenticate the
sender, fetch the referenced source, verify the wheel, independently recompile
artifacts or establish that execution occurred. Establish the observation's
origin separately through the linked CI run and source history.

The original packet refers to source
`59ad8139813ac5eb7b891907b3d74ebb06059a67` and
[its installed Linux job](https://github.com/kirchherr/TUC/actions/runs/38277950014/job/114907922282).
Its original auditor source is preserved byte-for-byte in
`archive/audit_native_receipt_59ad813.py.txt`. The current auditor additionally
checks strict digest formats and relationships between the three contexts;
the original packet and hashes are unchanged.

## Make a fresh native observation

Use an independently controlled disposable Linux x86-64 environment with a
working local Docker daemon. Review the existing
[runtime requirements](../../docs/BOUNDED_CPU_APPLICATION.md) before
execution. From a checkout at the exact revision being reviewed:

```sh
tuc_source="$(pwd)"
tuc_reproduction="$(mktemp -d)"
python -m venv "$tuc_reproduction/build-env"
"$tuc_reproduction/build-env/bin/python" -m pip install --require-hashes -r "$tuc_source/requirements/ci.txt"
"$tuc_reproduction/build-env/bin/python" -m pip wheel --no-deps --no-build-isolation --no-index "$tuc_source" --wheel-dir "$tuc_reproduction/wheels"
python -m venv "$tuc_reproduction/run-env"
"$tuc_reproduction/run-env/bin/python" -m pip install --require-hashes -r "$tuc_source/requirements/ci.txt"
"$tuc_reproduction/run-env/bin/python" -m pip install --no-deps --no-index "$tuc_reproduction"/wheels/tuc-*.whl
mkdir -m 700 "$tuc_reproduction/client"
cp "$tuc_source/integration/bounded_model_application/native_consumer.py" "$tuc_reproduction/client/"
cp "$tuc_source/integration/bounded_model_application/audit_native_receipt.py" "$tuc_reproduction/client/"
cd "$tuc_reproduction/client"
export PATH="$tuc_reproduction/run-env/bin:$PATH"
unset PYTHONPATH
python -I -c 'import pathlib,sys,tuc; assert pathlib.Path(tuc.__file__).resolve().is_relative_to(pathlib.Path(sys.prefix).resolve())'
python -I native_consumer.py
python -I native_consumer.py --run
python -I -S audit_native_receipt.py record.json
```

Both virtual environments, the wheel and the copied client stay outside the
checkout. Keep the new directory for reviewing its observation.

The first command only prints a candidate. `--run` explicitly builds and runs
the existing isolated CPU path; it creates `workspace` and `record.json` in the
client directory. Use a fresh directory for each observation. Success requires
three calls, four rejected controls and an empty workspace after every call.
The audit must pass all 18 scalar comparisons. The full pinned workflow is
[`bounded-model-application.yml`](../../.github/workflows/bounded-model-application.yml).

Retain the exact source revision, wheel/source hashes, raw `record.json`, audit
output, command log and independently controlled environment identity. A new
observation becomes external evidence only when another party supplies its own
origin and execution record. Same-project CI and local replay do not establish
independent organizational reproduction. No performance, general model, GPU
or vendor-compatibility result follows from this fixed corpus.
