# Verified 0.2.0 engineering dry-run at 8044760

Recorded on 2026-11-13 for source
`8044760f5e474d71ac10f22f20f2f2fd0883fef3`. This is an engineering dry-run,
superseded for the M0 freeze by the image security refresh described below.
Its successful build and signatures do not establish release security
acceptance, independent M1 reproduction or permission to publish.

## Normal review and protected build

[PR #143](https://github.com/kirchherr/TUC/pull/143) merged normally by Squash,
after `mailactiveblue-blip` formally approved exact head
`a46c87d3ee32bbe6974af2156c4c79c741dfc553`. Two APPROVED submissions came from
one eligible Codeowner. The merged commit has one parent `103ec78810db608107f5884a5cb99cf2316219ad`
and the reviewed tree `f15226f3f0668b68208c4cd8a66bb6f0508c7268`.
The [actual rule suite](research-candidate-8044760/normal-merge-rule-suite.json)
passed all five evaluations, with result `pass`, rather than `bypass`.
This closes R4/R5's normal-review verification.

All 35 checks for that source completed: 33 successes and two expected skips.
The [main regression](https://github.com/kirchherr/TUC/actions/runs/43440580177/job/131936842727)
passed 7,771 tests with two skips, Ruff, strict Mypy for 169 source files and
the subsequent proof gates. The
[protected manual candidate build](https://github.com/kirchherr/TUC/actions/runs/43441263934/job/131939171399)
also passed 7,771 tests with two skips, using the separate hash-locked
`setuptools==84.1.0` toolchain. Distribution building, isolated wheel import,
the historical data-only replay, OCI verification, SBOM generation,
attestations and upload succeeded. No publishing job ran.

## Artifact and signature identities

The uploaded `tuc-research-candidate` artifact is ID `14047607738`, 69,137,701
bytes, expiring on 2026-12-13. Its ZIP SHA-256 is
`11208363756d63c917f47cc802abe5ad41bfc83ebd8c0573434a168da848107d`.
The downloaded ZIP matched that size and digest. Its closed ten-file list and
all nine manifest checksums passed. Wheel/sdist metadata identify `tuc==0.2.0`;
the SBOM and OCI descriptor checks passed again outside the producing job.

| Subject | SHA-256 |
| --- | --- |
| Candidate wheel | `b76c046db84bda314fc3a8c860be18c33213143ddb72b029f2a847548e2c3809` |
| Candidate sdist | `421bedf52926608458bd396acba2a9643306bcfeacb6b61bcb89eee232229d47` |
| Worker OCI archive | `8c358279315933b968c84451f67e11527ab8d951be21c500a553d4735e1ac00d` |
| Worker image manifest | `b58d9d994cb1a2ff676c2b79f1a870183b6bf3e0741c026f7920d18f4d7cceb4` |
| Candidate toolchain lock | `88847096f470feeb70f9e14bd61d2e9a7ab6f1ebf48b4beb069d1be08f05ab1f` |
| OCI archive verifier | `08b7eaefd32e2366c50f9727e8d73ca7a6405b1c084803b5abfb9ebac081a33c` |

The complete artifact checksums and repeated OCI result are retained in
[candidate-artifacts.json](research-candidate-8044760/candidate-artifacts.json).
Five signed [bundles](research-candidate-8044760/provenance-bundles.jsonl)
preserve distribution provenance/SBOM, worker provenance/SBOM and the original
Delta kit/receipt provenance. JSON serialization of these bundles is generated;
their signed payloads and signatures are retained.

Eight fresh cryptographic checks passed with the official portable GitHub CLI
2.104.0, acquired from its checksum-verified
[vendor release](https://github.com/cli/cli/releases/tag/v2.104.0).
The [verification record](research-candidate-8044760/provenance-verification.json)
records the verifier/root digests, checked subjects and certificate identity.
Policy bound repository ID `1260144654`, owner ID `159765997`, source and signer
digest `8044760`, `refs/heads/main`, GitHub-hosted execution, GitHub's OIDC
issuer, the research-candidate workflow, and run `43441263934`/attempt `1`.
The signed SBOM predicates equal the downloaded SBOM JSON objects.

After authenticating the artifact download and installing a separately trusted
GitHub CLI, provenance can be rechecked against the retained bundles:

```bash
gh attestation verify /path/to/tuc-0.2.0-py3-none-any.whl \
  --bundle docs/evidence/research-candidate-8044760/provenance-bundles.jsonl \
  --repo kirchherr/TUC \
  --signer-workflow kirchherr/TUC/.github/workflows/research-release-candidate.yml \
  --signer-digest 8044760f5e474d71ac10f22f20f2f2fd0883fef3 \
  --source-digest 8044760f5e474d71ac10f22f20f2f2fd0883fef3 \
  --source-ref refs/heads/main \
  --cert-oidc-issuer https://token.actions.githubusercontent.com \
  --predicate-type https://slsa.dev/provenance/v1 \
  --deny-self-hosted-runners --format json
```

The same policy applies to the other four attested files. For distribution and
worker SBOM checks, use `--predicate-type https://cyclonedx.org/bom` and compare
the signed predicate with the supplied SBOM. Use CLI-managed trusted roots;
the repository does not supply an alternative trust anchor. Bundle-only
verification cannot detect repository-name reuse, so also check the verified
certificate's numeric repository/owner IDs and the current GitHub repository.
Only verified certificate/timestamp fields supply OIDC identity and witnessed
time; producer-written provenance predicates do not independently prove a build.
See the [CLI verification policy](https://cli.github.com/manual/gh_attestation_verify).

## Actual installed-model observations

The [main installed-model job](https://github.com/kirchherr/TUC/actions/runs/43440580110/job/131936838036)
passed 552 selected tests and fresh core, session and installed CLI experiments.
It used a separately built CI wheel:
`ee31224150fcd7c25054f176f9e8ebdf5545224a141fefcf780ce9ef3bf5d88b`.
These observations do not certify execution of the candidate wheel above.

Six original JSON members are retained byte-for-byte from four GitHub artifact
ZIPs. [Their index](research-candidate-8044760/native-artifacts.json) records ZIP
IDs, sizes/digests, member hashes and three repeated offline audits. The source
is `8044760` and the artifact expiry is 2026-11-27.

- [Core CI packet](research-candidate-8044760/native-core-ci-record.json) and
  [project operator rehearsal](research-candidate-8044760/native-operator-operator-observation.json).
- [Session CI packet](research-candidate-8044760/native-session-ci-record.json) and
  [session observation](research-candidate-8044760/native-session-session-observation.json).
- [CLI CI packet](research-candidate-8044760/native-cli-ci-record.json) and
  [CLI observation](research-candidate-8044760/native-cli-cli-observation.json).

All three numerical records retain digest
`6a77307516b633d45b45f8efa4581076c854549491960652026b7219a3ff8bd8`.
From a trusted checkout, the unchanged standard-library auditor replays them:

```bash
for client in core session cli; do
  python -I -S integration/bounded_model_application/audit_native_receipt.py \
    --ci-packet "docs/evidence/research-candidate-8044760/native-$client-ci-record.json"
done
```

Each audit passed eighteen scalar checks and four rejection controls with
`tuc_imported=false` and `native_execution_performed=false`. The producer's
native observations are distinct: sessions recorded two builds, four native
calls, three successes, sequences `[1,2,1]`, terminal/closed cleanup; CLI
recorded three successes, seven rejected commands, batch `[1,2]`, single `1`
and clean workspaces. Lifecycle counts and execution origin require review of
the trusted consumer and run log; arbitrary JSON cannot authenticate them.
The rehearsal explicitly retains `external_origin_verified=false`.

## Security review and refresh

The dry-run's valid provenance identifies its old Python worker image; it does
not make that image current or vulnerability-free. The
[scan summary](research-candidate-8044760/image-security-triage.json) records
Trivy 0.76.2, the vendor archive/executable hashes, vulnerability database
timestamp/digest and exact image/report identities. Scans inspected the image
without executing it. Counts are advisory/package matches, not demonstrated
exploits or distinct CVE counts.

The actual old worker had three critical and twelve high matches with an
available Debian fix. For example Debian lists installed Perl
`5.36.0-7+deb12u3` as affected and `+deb12u4` as fixed for
[CVE-2026-13221](https://security-tracker.debian.org/tracker/CVE-2026-13221);
installed OpenSSL `3.0.20-1~deb12u2` is corrected in `3.0.22-1~deb12u2` for
[CVE-2026-84782](https://security-tracker.debian.org/tracker/CVE-2026-84782).

The replacement official Linux/amd64 Python manifest resolves to
`0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4`,
with CPython 3.12.16. Its separate base-image scan has zero critical/high
matches with an available fix. This does not claim zero findings: that base
still reports 2 critical, 96 high, 139 medium, 108 low and 4 unknown OS matches,
plus six pip matches. The updated research Dockerfile removes installed pip
and ensurepip after the locked binary NumPy installation. The installed source
converter remains copy-only/offline and disallows pip, Perl and SQLite imports;
it inherits the base's unused pip files. Reachability and residual-finding
review remain required; the newer base scan is not a rebuilt-worker scan.

The [Python image resolution](research-candidate-8044760/python-image-resolution.json)
retains the official tag index and selected platform manifest identities.
The new Dockerfile, context allowlist and material SBOM profile are separate
from the byte-frozen historical Dockerfile/SBOM generator and v0 reports.
The active installed converter uses the refreshed fixed base without adding
build commands or widening the trusted-module/import closure.

[Action/tool triage](research-candidate-8044760/action-security-triage.json)
found no indexed active reviewed advisories for the five pinned Actions or
Buildx 0.34.1. BuildKit 0.30.0 matches
[custom-frontend sandbox bypass](https://github.com/moby/buildkit/security/advisories/GHSA-7236-3392-c5c6)
and [group-parsing DoS](https://github.com/moby/buildkit/security/advisories/GHSA-72x6-4j93-7w86);
the vendor fixes both in 0.31.1+. Trusted frontends/base images mitigate the
historical setup. The active candidate/image-check paths move to reviewed
BuildKit 0.35.0, with no matching indexed advisories, pinned by the
[resolved Linux/amd64 digest](research-candidate-8044760/buildkit-image-resolution.json).
CDI remains disabled and insecure entitlements remain absent.

The [PyPI triage](research-candidate-8044760/python-dependency-triage.json)
applies to the identical candidate/worker lock contents at reviewed head
`a46c87d`: hashes matched vendor assets and no active advisories were reported
for those locked versions. It excludes the historical CI lock and base-image
packages. The historical setuptools 84.0.0 LOW alert remains visible; the
candidate uses 84.1.0. Availability of the open version-update PRs alone does
not establish a vulnerability or permit changing historical proof inputs.

## Remaining release gates

The owner-approved [legacy workflow retirement](research-candidate-8044760/publisher-retirement.json)
was read back as `disabled_manually`; CI and the research-candidate workflow
remain `active`. Both old tag publication and old manual dry-runs are stopped.
No tag, GitHub release or PyPI publication was created. A reviewed replacement
publisher and actual PyPI Trusted Publisher binding remain M2 work.

M0 still needs the security refresh merged through normal review, its actual
updated image built/scanned, residual findings assessed, and a protected
candidate run with new source/lock/wheel/image/verifier identities. Repeat the
applicable isolated-wheel/native checks; these source changes cannot reuse
the old wheel's result. M1 then needs an independently controlled operator
running the accepted supplied wheel with attributable core/session/CLI output.
The older operator runner builds its own wheel with the historical lock and
must not be described as verification of a supplied candidate wheel.
