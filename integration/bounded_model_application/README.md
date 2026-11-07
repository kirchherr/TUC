# Reproduce the bounded model application observation

This directory contains the fixed installed CPU consumer, a Python standard-
library auditor and the original CI observation. The consumer runs three model
contexts and four rejection controls. The auditor checks 18 exact FP32 results,
the fixed model identities and request/response integrity without importing TUC
or executing native code.

## Replay the retained observation

The [native evidence workflow](https://github.com/kirchherr/TUC/actions/workflows/bounded-model-application.yml)
publishes the `bounded-model-application-audit-kit` artifact after a successful
build and isolated replay. It contains a ZIP and its SHA-256 checksum. See the
[acceptance handoff](../../docs/BOUNDED_MODEL_APPLICATION_HANDOFF.md) for download,
verification and the remaining external evidence obligation.

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

To build the same distribution from a pinned repository checkout, with Python
and Git available, use an existing output directory:

```sh
python -I -S scripts/build_model_application_audit_kit.py --output /existing/output/tuc-model-application-audit-kit.zip
```

Run this command from the repository root. Git must be installed at an absolute
PATH location outside the checkout. The builder reads an exact committed Git
snapshot for its source inputs, ignores edits to those inputs and untracked
notes, and never imports or executes the packaged sources. Use the versioned
builder from that pinned commit. The stored ZIP has eight fixed flat members,
fixed timestamps, regular non-executable file modes, source identity and internal
checksums. Each source file is capped at 64 KiB; the ZIP is capped at 256 KiB.
The project LICENSE and NOTICE are included from the same commit.
Symlinks/submodules, missing or oversized sources and existing output targets
reject. Source and checksums must be compared with a trusted origin separately.

## Make a fresh native observation

Use an independently controlled disposable Linux x86-64 environment with
CPython 3.12, Git and a working local Docker daemon. Review the existing
[runtime requirements](../../docs/BOUNDED_CPU_APPLICATION.md) before
execution. Check out the trusted revision to be reviewed. Give the explicit
`run` command an unused output path outside the checkout:

```sh
commit="$(git rev-parse --verify HEAD)"
python3.12 -I -S scripts/reproduce_model_application.py run \
  --source-commit "$commit" --output "$HOME/tuc-model-observation"
```

The runner snapshots only the committed build files and the fixed client and
auditor. It downloads the binary wheels in `requirements/ci.txt` with hash
verification. Separate build and run environments install from that local
download, and the wheel is built without fetching further packages. The
installed client runs outside the checkout with the existing local Docker
controls. Docker may need to fetch the pinned base images. A failed run leaves
its working directory for diagnosis and does not emit a success observation.

Success writes `operator-observation.json` with the raw record, audit, source
revision, wheel and source hashes, Python platform and completed command
stages. Retain the directory and your terminal or CI log. Send the JSON and
the provenance of your run through a channel the reviewer can attribute to
you. Include who controls the environment, the reviewed source revision and
the observed wheel SHA-256. The JSON includes no host paths, account names,
executable code or wheel bytes.

## Review the returned observation

From a trusted checkout of the same reviewed commit, use Python 3.11 or later
and Git; this command requires neither Docker nor TUC installation:

```sh
python -I -S scripts/reproduce_model_application.py verify \
  --source-commit "$commit" /path/to/operator-observation.json
```

If the operator supplies the wheel digest separately, add
`--expected-wheel-sha256` with that digest to compare the two records.
`verify` checks the bounded data against the committed client, lock and
auditor, then recomputes all 18 scalar comparisons and four rejection checks
using the trusted auditor. It reports `external_origin_verified=false` and
`native_execution_performed=false`: arithmetic and identity consistency do
not authenticate the operator, prove Docker execution, or attest the wheel.

The [CI rehearsal](../../.github/workflows/bounded-model-application.yml)
runs this procedure and uploads a data-only example. External acceptance
requires a separately attributable observation from an independently
controlled environment. No performance, general model, GPU or
vendor-compatibility result follows from this fixed corpus.
