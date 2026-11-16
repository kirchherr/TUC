# Bounded research candidate at fdfcc19

Recorded on 2026-11-16 for source
`fdfcc193b0b42405e3e48ea6ace1bdfbea066536`. This source normally merged the
security refresh in [PR #144](https://github.com/kirchherr/TUC/pull/144).
The protected candidate build, eight consumer-side signature checks and the
actual-image scan are complete. This packet proposes the exact M0 pin and
supplied-wheel procedure for adoption through normal Codeowner review and
required checks. M1 independent acceptance and M2 publication remain open.

## Normal review

Eligible Write-enabled Codeowner `mailactiveblue-blip` submitted APPROVED review
`5916222502` at `2026-11-16T07:10:55Z`, for exact head
`fd257f2ac3f8775f54f64e98011ae8e947bebe32`. All 62 head checks completed:
60 successes and two expected skips. The normal Squash merge used that exact
head as its compare-and-swap condition. The resulting single-parent commit has
parent `8044760f5e474d71ac10f22f20f2f2fd0883fef3` and tree
`13808f2e8cd586efb8e20075020564a371682686`, identical to the reviewed tree.

Actual rule suite `5141623491` returned `pass` for all five active evaluations:
required status checks, linear history, pull request review, non-fast-forward
protection and deletion protection. No bypass or repository-rule change was
used. The actual rule-suite receipt is retained with this candidate evidence.

All 33 automatic main checks completed: 31 successes and two expected skips. The
[main regression](https://github.com/kirchherr/TUC/actions/runs/43822210038/job/133147661429)
passed 7,778 tests with two skips in 1,732.59 seconds, Ruff, strict Mypy for
169 source files and all subsequent proof gates. On main pushes the reviewed
security workflow skips PR-only Dependency Review; its real exact-head PR
check passed and the normal merge's required-check evaluation passed.
The second main skip is the branch/PR full-model regression, covered by main's
root regression. These are workflow-defined skips, not bypassed failures.

The new [protected candidate build](https://github.com/kirchherr/TUC/actions/runs/43826307479)
was dispatched once after those checks and the current controls were verified.
It is a successful manual `refs/heads/main` run for this exact source, attempt
one, with no publishing job. Its [full regression](research-candidate-fdfcc19/candidate-full-regression.json)
passed 7,778 tests with two skips in 1,291.59 seconds, Ruff and strict Mypy for
169 source files. Distribution building, isolated wheel installation/import,
historical data-only replay, OCI verification, SBOM generation, attestations
and upload passed. Including the candidate, all 34 source checks completed:
32 successes and two expected skips. The [control readback](research-candidate-fdfcc19/candidate-controls.json)
records the active main/tag/environment protections and disabled old publisher.

## Exact candidate and signatures

The uploaded `tuc-research-candidate` artifact is ID `14207209811`, 46,819,548
bytes, expiring on 2026-12-16. Its downloaded ZIP matched SHA-256
`209fa2ccff119b22aced513bf66b37f7c1d4b8ad0f5e2f7cf7463ce804b76f72`.
The closed ten-file set and all nine manifest checksums passed; package
metadata identifies `tuc==0.2.0`. Both SBOMs and all eight research-worker
source/context material hashes match the exact source's LF Git blobs.

| Subject | SHA-256 |
| --- | --- |
| Candidate wheel | `db258c3ca5cb2861779ebdfbb6b2d6d6991d99ec27c1f40616a3f85d6a8ebf85` |
| Candidate sdist | `f02d70a296bf3f16fe68eaa0a59e37da35d10e8197be9aab08620555df76ab62` |
| Worker OCI archive | `3ab4ade87e13549ed16a30427b454a64cbb6cb7b41f3bf3eac37f0f0c52e16d7` |
| Worker image manifest | `755d79589185ef522cee006d5597a4d9b9c4692b271ed906a626d3ff590243fc` |
| Worker image config | `e860fa5016c6a7650bc61d4f460a9c77202917c7e9c164aae6ca2877f32c7408` |
| Candidate toolchain lock | `88847096f470feeb70f9e14bd61d2e9a7ab6f1ebf48b4beb069d1be08f05ab1f` |
| OCI verifier | `08b7eaefd32e2366c50f9727e8d73ca7a6405b1c084803b5abfb9ebac081a33c` |
| Numerical auditor | `aedef34c29ac211415595f39fbb1ecb47b3690cc9b5c6b51a9b4c603d020f231` |

The [complete identities and repeated OCI result](research-candidate-fdfcc19/candidate-artifacts.json),
[manifest](research-candidate-fdfcc19/SHA256SUMS),
[package SBOM](research-candidate-fdfcc19/package.cdx.json),
[worker SBOM](research-candidate-fdfcc19/worker.cdx.json) and
[build-material pins](research-candidate-fdfcc19/build-material-pins.json) are
retained. Original authenticated distributions and OCI bytes remain the
handoff inputs; rebuilding them would not preserve these identities.

Five [signed bundles](research-candidate-fdfcc19/provenance-bundles.jsonl) retain
distribution provenance/SBOM, worker provenance/SBOM and Delta kit/receipt
provenance. Eight fresh checks passed with the checksum-verified vendor GitHub
CLI 2.104.0 and current managed/TUF-verified roots. The
[verification record](research-candidate-fdfcc19/provenance-verification.json)
binds repository ID `1260144654`, owner ID `159765997`, source and signer
`fdfcc193b0b42405e3e48ea6ace1bdfbea066536`, `refs/heads/main`, GitHub-hosted
execution, GitHub's OIDC issuer, the research-candidate signer workflow and
run `43826307479`/attempt one. Signed SBOM predicates equal the downloaded JSON.
The Delta receipt remains byte-identical to its original golden observation;
its new provenance does not represent a new independent model experiment.

The [supplied-wheel operator procedure](../SUPPLIED_CANDIDATE_OPERATOR.md)
includes the consumer verification command. Use CLI-managed roots, verify
numeric IDs against the current repository and check certificate/run identity;
producer-written predicates and bundle-only repository names do not establish
those facts by themselves. The subsequent handoff controller has its own
recorded source/digest and leaves the candidate wheel and consumers unchanged.

## Supplied-wheel project rehearsal

The [actual supplied-wheel job](https://github.com/kirchherr/TUC/actions/runs/43832760341/job/133181809983)
passed thirteen rejection/pin tests, provenance/certificate/current-repository
checks and all three native model consumers with candidate wheel `db258c3...`.
It installed the authenticated local wheel with `--no-deps --no-index` and
did not build a replacement TUC wheel. Its controller revision is
`b57bcee8cf217fccda362f8dbb21fc7099fe74e6`, with LF Git/source digest
`78a1e585b4d3f7cae3504bad607f9aea75445941fdd70305b22a280652c58f78`;
the package/consumer source remains the separately identified `fdfcc19`.

The [observation index](research-candidate-fdfcc19/supplied-wheel-observations.json)
binds actual artifact `14209496688`, 22,548 ZIP bytes, transport SHA-256
`f8e45618395f6411d9670d4f24c15c962570921a139b147fd64c381e5900c3c3`,
all fourteen original members and three fresh offline audits. The run used
Linux x86-64, CPython 3.12.16, Docker 28.0.4/API 1.48 and cgroup v2.
The actual [rehearsal record](research-candidate-fdfcc19/supplied-wheel/rehearsal.json)
retains the fixed source/material identities, original record digest and
`tuc_wheel_rebuilt=false`.

- [Core packet](research-candidate-fdfcc19/supplied-wheel/core/ci-record.json),
  [original record](research-candidate-fdfcc19/supplied-wheel/core/record.json)
  and [audit](research-candidate-fdfcc19/supplied-wheel/core/audit.json).
- [Session packet](research-candidate-fdfcc19/supplied-wheel/session/ci-record.json)
  and [actual lifecycle](research-candidate-fdfcc19/supplied-wheel/session/session-observation.json):
  two builds, four native calls, three successes, `[1,2,1]`, one closed-session
  rejection and clean workspaces.
- [CLI packet](research-candidate-fdfcc19/supplied-wheel/cli/ci-record.json)
  and [actual observation](research-candidate-fdfcc19/supplied-wheel/cli/cli-observation.json):
  three successes, seven rejected commands, batch `[1,2]`, single `1`, installed
  execution outside the checkout and clean workspaces.

All three original numerical records have digest `6a773075...`; three fresh
stdlib-only audits each passed eighteen scalars and four rejection controls,
with `tuc_imported=false` and `native_execution_performed=false`. Original
JSON bytes are retained; the producer's native execution and lifecycle are
separate facts tied to its actual source/run. This is project-controlled
readiness evidence, with independent acceptance explicitly false.

M0 adoption uses this exact candidate, recorded scopes and passing supplied-wheel
rehearsal when the packet is normally Codeowner-approved and merged after its
required checks. It authorizes no tag or publication. M1 next needs an
attributable independently controlled operator; none is assigned. M2 still
requires M1, its reviewed replacement publisher/actual PyPI binding and the
normal release/environment approvals.

## Current actual-image review

The [scan summary](research-candidate-fdfcc19/image-security-triage.json) and
[complete original report](research-candidate-fdfcc19/worker-vulnerability-scan.json)
identify Trivy 0.76.2, the fresh Nov16 database, exact archive/config and report
SHA-256 `64d29e454f563b1af0a6e132666e0970417b1117dec7923f936f9a016ed47fa4`.
The scanner processed the verified outer OCI layout without executing the
image, with no ignore entries or ambient Trivy overrides. It reports 105 OS
packages, zero matches with an available fix and zero Python-package matches.
Remaining matches are 2 critical, 100 high, 142 medium, 108 low and 5 unknown;
these are advisory/package matches, not confirmed exploits or distinct CVEs.

The [scoped residual review](research-candidate-fdfcc19/residual-image-review.json)
retains every finding and its limits. The critical
[MiniZip entry](https://security-tracker.debian.org/tracker/CVE-2023-45853)
matches Debian's zlib source package, whose Bookworm binary omits affected
MiniZip code; the inventory contains no MiniZip package. The critical
[SQLite entry](https://security-tracker.debian.org/tracker/CVE-2025-7458)
requires executable SQL, which the fixed six-module worker does not expose.
Kerberos/GSSAPI, system/device tools, terminal/Perl/compression, SQLite and the
new PAM/C++/dpkg findings have explicit path assessments. This scoped static
review recommends the bounded research freeze for normal review; it does not
grant production admission or general vulnerability-free status.

The [local exact-image observation](research-candidate-fdfcc19/exact-candidate-runtime-probe.json)
loaded the signed config and all seven unchanged layer diff IDs through a
transport-only Docker archive adaptation. Its actual canary observed CPython
3.12.16, no NumPy/pip/ensurepip, UID/GID 10001, seccomp 2, no-new-privileges,
zero effective capabilities, read-only rootfs, loopback-only networking,
1 GiB memory, 32 PIDs and one CPU. Its local Docker Desktop engine uses cgroup
v1, so the unchanged worker failed before request parsing. This is explicitly
`CANARY_PASS_PROTOCOL_UNSUPPORTED`, not a positive protocol run. Containers and
the newly loaded image were removed; no host configuration was changed.
The [existing worker contract](../OCI_SOURCE_INGESTION_RESEARCH_WORKER.md)
requires cgroup v2. The
[successful main profile job](https://github.com/kirchherr/TUC/actions/runs/43822209929/job/133147660704)
tested the same reviewed source/materials in its separately built cgroup-v2
image, including actual request/response, injected context exclusion and denied
host-network entitlement. Its result is not relabeled as execution of the
candidate archive.

Active [action/tool triage](research-candidate-fdfcc19/action-security-triage.json),
[consumer-tool triage](research-candidate-fdfcc19/consumer-verifier-advisory-triage.json)
and [Python dependency triage](research-candidate-fdfcc19/python-dependency-triage.json)
retain fresh vendor/API observations with explicit coverage limits. The
[open update-PR review](research-candidate-fdfcc19/update-queue-triage.json)
records actual changed paths and the separate handling of historical proof
inputs; no update PR was merged by this packet.

## Main installed-model observations

The [main installed-model job](https://github.com/kirchherr/TUC/actions/runs/43822210153/job/133147661433)
passed 552 selected tests in 29.65 seconds and fresh core, session and installed
CLI experiments. It used a separately built CI wheel:
`965bfa94fdc06241fb1bd9d2d2fa9ba2822b5de4fdffb33c677b6aaa7dd28ad6`.
These observations identify this CI wheel; supplied-candidate-wheel execution
is a separate experiment.

Six original JSON members are retained byte-for-byte from four GitHub artifact
ZIPs. [Their index](research-candidate-fdfcc19/native-artifacts.json) records ZIP
IDs, sizes/digests, member hashes and three repeated offline audits. The source
is `fdfcc19` and the original CI artifacts expire on 2026-11-30.

- [Core CI packet](research-candidate-fdfcc19/native-core-ci-record.json) and
  [project operator rehearsal](research-candidate-fdfcc19/native-operator-operator-observation.json).
- [Session CI packet](research-candidate-fdfcc19/native-session-ci-record.json) and
  [session observation](research-candidate-fdfcc19/native-session-session-observation.json).
- [CLI CI packet](research-candidate-fdfcc19/native-cli-ci-record.json) and
  [CLI observation](research-candidate-fdfcc19/native-cli-cli-observation.json).

All three numerical records retain digest
`6a77307516b633d45b45f8efa4581076c854549491960652026b7219a3ff8bd8`.
From a trusted checkout, the unchanged standard-library auditor replays them:

```bash
for client in core session cli; do
  python -I -S integration/bounded_model_application/audit_native_receipt.py \
    --ci-packet "docs/evidence/research-candidate-fdfcc19/native-$client-ci-record.json"
done
```

Each audit passed eighteen scalar checks and four rejection controls with
`tuc_imported=false` and `native_execution_performed=false`. The producer's
native observations are separate: sessions recorded two builds, four native
calls, three successes, `[1,2,1]`, closed-session rejection and clean workspaces.
CLI recorded three successes, seven rejected commands, batch `[1,2]`, single
`1`, installed execution outside the checkout and clean workspaces. Lifecycle
and execution-origin claims require the trusted consumer and actual run log;
the numerical auditor cannot establish them from arbitrary JSON. The project
rehearsal retains `external_origin_verified=false`.

The earlier [8044760 dry-run](RESEARCH_CANDIDATE_8044760.md), original numerical
corpus, legacy Docker/SBOM/CI proof materials and their observations remain
unchanged. The new evidence does not relabel those historical measurements.

## Current converter base scope

The [fresh base-image observation](research-candidate-fdfcc19/source-converter-base-security.json)
uses Trivy 0.76.2 and the 2026-11-16 database against the exact pinned Python
base. It records 2 critical, 100 high, 142 medium, 108 low and 5 unknown OS
advisory/package matches, without an available OS fix in that database. The
base's unused pip 25.0.1 metadata has five medium and one low match with fixes.
The installed copy-only source converter inherits those files but neither
invokes an installer nor admits its imports. Its fixed six-module closure
exposes no package/archive installation input. This is a static path assessment;
the base observation does not substitute for scanning the packaged candidate
worker, which removes pip/ensurepip.

Compared with the Nov13 database, the fresh base scan adds four high package
matches for [PAM namespace traversal](https://github.com/linux-pam/linux-pam/security/advisories/GHSA-f9p8-gjr4-j9gx),
three medium matches for [libstdc++ stream buffering](https://security-tracker.debian.org/tracker/CVE-2026-125709)
and one unknown match for [dpkg quilt-source extraction](https://security-tracker.debian.org/tracker/CVE-2026-91094).
[Debian's PAM tracker](https://security-tracker.debian.org/tracker/CVE-2025-6020)
still lists Bookworm's version as affected because the earlier patch was not
applied correctly. The scoped code review finds no PAM
authentication/session setup, C++ stream consumer, dpkg invocation or source
package input in the worker. Its fixed non-root Python entrypoint, no command
dispatch, capability drop, read-only rootfs and bounded plain-JSON request
preserve that boundary. These are reachability inferences for this declared
experiment, not claims that the underlying packages are globally safe. The
actual candidate scan and residual review below determine its freeze proposal.
