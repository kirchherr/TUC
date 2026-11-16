# Supplied bounded-model candidate procedure

This procedure uses the protected candidate from source
`fdfcc193b0b42405e3e48ea6ace1bdfbea066536`. It installs the supplied 0.2.0 wheel;
it does not rebuild TUC. The separate [candidate evidence](evidence/RESEARCH_CANDIDATE_FDFCC19.md)
binds the source, artifact manifest, signed bundles, lock and verifier identities.
The script and this procedure are subsequent handoff tooling; their revision and
the script's actual digest must also be recorded in the returned observation.
The Actions candidate artifact expires on 2026-12-16. Preserve the original
authenticated bytes; the procedure accepts the exact local wheel even after
artifact expiry. The CI rehearsal fails if that fixed download is unavailable
and never silently rebuilds or substitutes a newer wheel. It runs automatically
for changes to this handoff tooling/pin, and can be dispatched manually; unrelated
changes do not acquire an expiring-artifact dependency. After M2, a separately
reviewed transition can use the byte-identical published distribution.

## Environment and trusted inputs

Use an operator-controlled disposable Linux x86-64 machine with CPython 3.12,
Git at `/usr/bin/git`, Docker at `/usr/bin/docker`, venv/pip, a local
`/var/run/docker.sock` and the existing
bounded native runtime controls. Running the command below explicitly permits
the fixed reviewed consumers to build and execute their isolated C11 workload.
Dependency installation uses the candidate's hash-locked research toolchain;
the installed TUC package comes solely from the authenticated local wheel.

Start from a trusted checkout containing this reviewed script and evidence.
Download `tuc-research-candidate` from protected workflow run `43826307479`.
Its artifact ID, ZIP digest/size and closed file manifest are recorded in the
candidate evidence. Authenticate those bytes and verify the supplied wheel's
provenance before installation, using a separately trusted GitHub CLI and its
managed trust roots:

```bash
gh attestation verify /absolute/path/tuc-0.2.0-py3-none-any.whl \
  --bundle docs/evidence/research-candidate-fdfcc19/provenance-bundles.jsonl \
  --repo kirchherr/TUC \
  --signer-workflow kirchherr/TUC/.github/workflows/research-release-candidate.yml \
  --signer-digest fdfcc193b0b42405e3e48ea6ace1bdfbea066536 \
  --source-digest fdfcc193b0b42405e3e48ea6ace1bdfbea066536 \
  --source-ref refs/heads/main \
  --cert-oidc-issuer https://token.actions.githubusercontent.com \
  --predicate-type https://slsa.dev/provenance/v1 \
  --deny-self-hosted-runners --format json > wheel-provenance.json
```

Check the verified certificate's repository ID `1260144654`, owner ID
`159765997`, GitHub-hosted environment, `workflow_dispatch` trigger and
`https://github.com/kirchherr/TUC/actions/runs/43826307479/attempts/1` identity.
Check those numeric IDs against the current GitHub repository to detect name
reuse. Producer-written predicate fields alone do not authenticate build origin.
The [complete verification record](evidence/research-candidate-fdfcc19/provenance-verification.json)
also covers the sdist, worker and signed SBOM predicates.

## Execute the supplied-wheel probe

Ensure the candidate's fixed source objects are available in the trusted
checkout. The runner reads only a finite list of blobs from that exact source,
including the lock, unchanged three consumers, numerical auditor and CLI
fixtures. The controller uses only stdlib and committed blobs; TUC imports
occur in the fresh installed run environment.
Choose a new absolute output directory outside the checkout; its parent must
already exist. Existing outputs are rejected without modification.

```bash
git fetch --no-tags --depth=1 https://github.com/kirchherr/TUC.git \
  fdfcc193b0b42405e3e48ea6ace1bdfbea066536
python3.12 -I -S scripts/rehearse_supplied_model_wheel.py run \
  --wheel /absolute/path/tuc-0.2.0-py3-none-any.whl \
  --output /absolute/path/outside-checkout/tuc-supplied-fdfcc19
```

The runner first authenticates the wheel's fixed digest, then creates a fresh
environment and installs locked requirements plus that wheel using
`--no-deps --no-index`. It checks installed package/console origin and `pip check`,
then invokes the existing core, session and CLI consumers from separate fresh
directories outside the checkout. Each unchanged stdlib-only auditor checks
eighteen scalars and four rejection controls. The lifecycle checks require two
session builds, four native calls, three successes, `[1,2,1]`, closed-session
rejection and cleanup; the CLI checks require three successes, seven rejected
commands, batch `[1,2]`, single `1`, outside-checkout installation and cleanup.

The runner checks the candidate wheel independently of the CI-built wheel
recorded in the main engineering observations. A changed wheel fails before
Git, pip or native execution. Source/lock or consumer changes require review
and an explicit revised identity; the old v0 self-building operator envelope is
unchanged and must not be relabeled as supplied-wheel execution.
Its environment record includes the actual local daemon/API version, kernel
and cgroup version as well as Python/OS/architecture; these facts still require
an attributable operator/environment-control review for M1.

## Return and review

Return `rehearsal.json`; all three clients' `record.json`, `audit.json` and
`ci-record.json`; `session/session-observation.json`;
`cli/cli-observation.json`; the verified wheel provenance; and the attributable
command/run log. The runner retains per-step stdout/stderr under the output
directory. Review local paths and environment details before sharing logs.
Also return your identity, who administers the environment, the handoff-tool
revision/digest, exact source/wheel identity and the agreed return channel.

`rehearsal.json` deliberately records `external_origin_verified=false` and
`independent_operator_acceptance=false`. Passing arithmetic, lifecycle checks
or a project-controlled CI probe cannot authenticate operator independence.
An eligible reviewer must assess the attributable external origin and scope
separately before M1 can close. No independent operator is currently assigned.

This procedure supplies no publishing authorization. M2 still requires M0/M1
acceptance, a reviewed replacement publisher, actual PyPI binding and the normal
release/environment approvals. The historical publisher remains disabled.

## Procedure review boundary

The input is one wheel with the fixed reviewed name and SHA-256, plus a new
outside-checkout output path. The controller does not accept source/model text,
commands, replacement consumers, alternate locks or an arbitrary expected
digest. Wheel bytes are read once through a bounded regular-file/no-follow
check; their digest must pass before Git, installation or native authority is
reached. The finite Git blob list cannot invoke checkout hooks or text filters.
Subprocesses use argument arrays and a clean environment, with the existing
native consumers and timeouts. Locked dependencies are binary wheels; the TUC
installation is local and index-free. Final `rehearsal.json` is emitted only
after every numerical and lifecycle check succeeds. A failed attempt preserves
its fresh directory for diagnosis and requires a new directory for a rerun.

The [negative tests](../tests/test_supplied_model_wheel_rehearsal.py) cover
changed/name-mismatched wheels before subprocess authority, unsupported file
types, empty/oversized inputs, symlinks/FIFOs, existing outputs and checkout
path redirection. The separate read-only CI workflow verifies the actual fixed
wheel provenance and executes the procedure with that supplied wheel. Its
artifact and source identify project-controlled readiness evidence. Output JSON
and the passing tests do not authenticate an external operator's identity.
