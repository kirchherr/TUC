# Release Security

This document defines TUC's release artifact and publishing controls.

## Prepared Research Candidate

The next package version is **0.2.0**, prepared for the bounded CPU model
research release in the [completion plan](PROJECT_COMPLETION_PLAN.md). It adds
the existing model Python APIs, reusable sessions and installed `tuc-model-app`
single/batch interface to the package version previously published as 0.1.0.
The package remains pre-alpha. Preparing this version does not freeze a source
revision, authorize publication or establish independent acceptance.

The model execution evidence covers Linux x86-64, CPython 3.12, local Docker
and the existing all-C11 path, with its static FP32, graph, shape, request and
cumulative session budgets. Other operating systems, Python versions, native
targets and physical cross-vendor execution need their own applicable
validation. The package's `>=3.11` Python metadata is an installation constraint,
not evidence that the full native execution path has been validated everywhere
it can be installed. C11/CUDA/mixed planning remains hardware-neutral; actual
model execution admits only the stated all-C11 boundary.

M0 still requires verified repository and publishing controls, a successful
normal Codeowner review, security triage, exact-revision CI and a protected
non-publishing release dry-run. Record the accepted source, lock, wheel, image
and verifier identities from that run before M1. M1 requires fresh observations
from an independently controlled operator; project CI and the historical
Objective Delta receipt do not supply that acceptance. M2 then governs
publication and its separate approvals.

The 0.2.0 preparation adds a separate
[research-candidate workflow](../.github/workflows/research-release-candidate.yml)
and [toolchain lock](../requirements/research-release.txt). It runs only through
manual dispatch on protected `main`, builds and attests artifacts, verifies the
worker attestation against its own workflow/source identity, and retains the
GitHub CLI verification JSON. It has no publishing job or tag/PR trigger.
The historical workflow, lock, v0 receipt writer and proof corpus remain intact.
Their v0 readiness report describes that historical path; it does not certify
this new candidate workflow. A successful candidate dry-run is still required.

The historical tag-triggered publisher remains configured. M0 must resolve its
retirement or replacement through a reviewed publishing migration before any
0.2.0 release tag is created. This source preparation neither disables that
workflow nor authorizes its use to publish the new candidate.

## Release Artifact Scope

The release workflow builds:

- Python source distribution.
- Python wheel.
- CycloneDX JSON SBOM.
- `linux/amd64` source-worker OCI Image Layout archive.
- Source-worker OCI verification report.
- Source-worker CycloneDX JSON SBOM.
- Objective Delta data-only reproduction kit and metadata-only replay receipt.
- SHA-256 checksum manifest.
- GitHub artifact attestations for build provenance and the SBOM.

Both paths upload GitHub Actions artifacts. Only the historical workflow has a
publishing job for protected `v*` tag pushes after `pypi` environment approval;
the new research-candidate workflow produces artifacts without publication.

The historical Linux x86_64 / CPython 3.12 toolchain is resolved in
`requirements/ci.txt`; the new candidate uses `requirements/research-release.txt`.
Every locked wheel is version- and SHA-256-pinned, installation uses
`--require-hashes`, and TUC's editable install disables dependency resolution and
build isolation. In the new candidate workflow, distribution builds disable build
isolation so the reviewed build-tool lock remains in effect. The fresh wheel
verification environment installs the same hash-locked requirements, installs
only the local wheel with dependency resolution and index access disabled,
checks dependency compatibility, and runs outside the checkout with
`PYTHONPATH` unset. CI and release tests use four fixed isolated workers from
the locked `pytest-xdist` wheel. Lock updates require normal dependency review.

The new research-candidate lock selects `setuptools 84.1.0` after reviewing
[GHSA-xmj3-9gf7-h52w](https://github.com/pypa/setuptools/security/advisories/GHSA-xmj3-9gf7-h52w).
The upstream advisory affects versions below 84.1.0 and describes a Windows
path escape in legacy wheel installation. The locked replacement wheel hash
was checked against upstream PyPI release metadata. The historical lock still
contains 84.0.0 because its exact bytes bind the accepted v0 proof. Its Linux
PEP 517 build does not reach the affected legacy Windows installation path;
it is not the toolchain for the new candidate. The package build-system minimum
remains compatible with that frozen research CI; it does not select the
candidate's actual builder. This documented transition does not replace the
remaining dependency, action, image and publishing-migration review.

## Trust Boundary

Release artifacts change TUC's downstream trust boundary because users may run
compiler code from those artifacts. A release build must therefore be treated as
more sensitive than ordinary CI.

Current controls:

- Release workflow permissions are least-privilege by default.
- Only the artifact-build job receives `attestations: write`; its OIDC token is
  used only for GitHub artifact attestations.
- The PyPI publishing job receives a separate OIDC token and no attestation
  permission.
- The PyPI publishing job is isolated from artifact building and test execution.
- Release workflow actions are pinned to reviewed commit SHAs.
- Buildx is version-pinned and BuildKit is version- and digest-pinned with CDI
  disabled and no insecure build entitlement allowlist.
- The workflow uses GitHub OIDC-backed artifact attestations rather than stored
  signing secrets.
- The workflow builds artifacts from repository source and does not run dynamic
  plugin, backend, or generated-artifact execution.
- SBOM generation is repository-owned Python code, not a third-party action.
- The source-worker base image is digest-pinned, Python requirements are
  hash-locked, and the Docker build context is allowlisted.
- Repository-owned code verifies the OCI descriptor graph, platform, non-root
  identity, working directory, entrypoint, command policy, and rootfs digests
  before attestation.
- Repository-owned code builds the Objective Delta kit deterministically,
  validates it without extraction, replays it through the installed release
  wheel, and compares the receipt byte for byte with reviewed evidence before
  attestation.
- Manual workflow runs are dry-runs. Publishing is restricted to `v*` tag pushes.

## Required For Publishing

Before TUC publishes to PyPI:

1. Protect release tags or restrict tag creation to maintainers.
2. Require `pypi` environment approval.
3. Use PyPI Trusted Publishing through OIDC.
4. Document the package verification command in the release notes.

See [Release governance](RELEASE_GOVERNANCE.md) for the required GitHub tag
ruleset and publishing-environment policy.

## Verification

Consumers or maintainers can verify GitHub artifact attestations with the GitHub
CLI once release artifacts are produced:

```bash
gh attestation verify dist/tuc-0.2.0-py3-none-any.whl -R kirchherr/TUC
gh attestation verify dist/tuc-0.2.0.tar.gz -R kirchherr/TUC
gh attestation verify dist/tuc-source-ingestion-worker.oci.tar -R kirchherr/TUC
gh attestation verify dist/tuc-objective-delta-reproduction-kit-v0.zip -R kirchherr/TUC
gh attestation verify dist/tuc-objective-delta-reproduction-receipt.v0.json -R kirchherr/TUC
```

The release workflow also performs policy-bound, same-run provenance
verification for the worker archive and adds a bounded verification receipt to
the checksum manifest. This confirms that the attestation fetched by that run
matches the archive digest, repository, signer workflow, commit, ref, OIDC
issuer, SLSA predicate, and GitHub-hosted runner policy. It does not replace the
consumer-side commands above or prove tag-ruleset enforcement.

The checksum manifest can be checked locally:

```bash
cd dist
sha256sum -c SHA256SUMS
```

## SBOM Format

The SBOM format is CycloneDX JSON 1.6. The package SBOM describes the Python
project and direct runtime dependencies from `pyproject.toml`. The worker SBOM
separately binds its digest-pinned Python base image, hash-locked NumPy wheel,
Dockerfile, requirements, worker source, and target platform.

Future native backends, bundled binaries, generated compiler plugins, or runtime
artifacts must extend this SBOM model before release.

## Non-Goals

- Publishing the worker to a public container registry.
- Treating same-run verification as independent consumer verification or
  protected tag-ruleset evidence.
- Long-lived signing keys.
- Executing generated backend artifacts during release.
- Claiming byte-reproducible wheel or source-distribution builds. The fixed
  Objective Delta data-only kit itself is deterministic by contract.
- Treating the maintainer release receipt as independent third-party
  reproduction.

See [OCI Source Worker Release Provenance](OCI_SOURCE_WORKER_RELEASE_PROVENANCE.md)
for the archive contract and remaining claim boundary.
