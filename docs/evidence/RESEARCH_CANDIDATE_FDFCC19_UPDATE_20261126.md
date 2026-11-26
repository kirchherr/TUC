# Candidate security follow-up: 2026-11-26

This supplements the [original candidate](RESEARCH_CANDIDATE_FDFCC19.md) and
[November 20 review](RESEARCH_CANDIDATE_FDFCC19_UPDATE_20261120.md). Candidate
source `fdfcc193b0b42405e3e48ea6ace1bdfbea066536`, wheel `db258c3c…`, OCI
archive `3ab4ade8…` and the original consumer/auditor bytes are unchanged.
M0 adoption still awaits normal Codeowner review of
[#145](https://github.com/kirchherr/TUC/pull/145). M1 and M2 remain open.

## Current image observation

The [actual full scan](research-candidate-fdfcc19-update-20261126/worker-vulnerability-scan.json)
uses Trivy 0.76.2 with its November 26 database. The
[triage](research-candidate-fdfcc19-update-20261126/image-security-triage.json)
records the database identity, expiry, tool digests and exact image identity.
The image was scanned without execution. No suppression was added.

| Advisory/package matches | November 20 | November 26 |
| --- | ---: | ---: |
| Critical | 2 | 2 |
| High | 99 | 100 |
| Medium | 142 | 148 |
| Low | 110 | 114 |
| Unknown | 12 | 18 |
| Total | 365 | 382 |
| Matches with an available fixed package in this database | 0 | 0 |
| Python-package matches | 0 | 0 |

These are package/advisory matches, not demonstrated exploits or distinct CVEs.
The [assessment](research-candidate-fdfcc19-update-20261126/assessment.json)
retains all nineteen added matches, two database removals and changed
classifications. The two critical matches and their earlier dispositions remain
unchanged. New non-seccomp entries concern PAM, SunRPC, OpenSSL encoding,
Zstandard, shadow helpers and Perl FTP. Their bounded worker reachability
inferences are explicit; no general vulnerability-free approval is implied.

## Host filter acceptance remains separate

Seven new database matches identify the image's `libseccomp2 2.5.4-1+deb12u1`.
The fixed Python worker does not call this library. Filters are installed by
the host runtime, whose library and policy are separate from the image inventory.

The [upstream syscall-load advisory](https://github.com/seccomp/libseccomp/security/advisories/GHSA-q75f-27j4-2h7j)
and [accumulator advisory](https://github.com/seccomp/libseccomp/security/advisories/GHSA-35x7-vh54-jvqf)
describe policy-dependent filter generation defects fixed in 2.6.2. They require
assessment of the actual runtime and applicable backports or generated BPF;
`Seccomp: 2` alone cannot establish correct enforcement. The assessment links
all seven advisories, including earlier issues now matched by the database.
Scanner `UNKNOWN` classifications do not supersede upstream severity.

R7 in the [completion plan](../PROJECT_COMPLETION_PLAN.md) records the open
M1/M2 host-filter acceptance requirement. The supplied-wheel CI now retains
fixed read-only runtime/package/Docker inventory as `OBSERVATION_ONLY`, with
`host_filter_patch_accepted=false`. The record identifies observations for
review; it does not authenticate daemon linkage, downstream patches or operator
control. Passing numerical/native tests supplies no automatic host acceptance.

## Patched and pinned signature verifier

[GitHub CLI 2.106.0](https://github.com/cli/cli/releases/tag/v2.106.0) was released
on November 25 with seven security fixes. The handoff workflow now explicitly
uses that reviewed binary for downloads, repository identity and attestations.
Its preparer authenticates the complete official archive before parsing it and
verifies the separately pinned Linux executable before writing a fresh private
tool directory. It performs no executable run or global installation.
The [release metadata](research-candidate-fdfcc19-update-20261126/verifier-release.json),
[vendor checksums](research-candidate-fdfcc19-update-20261126/gh_2.106.0_checksums.txt)
and [actual Linux preparation](research-candidate-fdfcc19-update-20261126/linux-verifier-preparation.json)
retain these identities. Boundary tests cover pre-authentication rejection,
special files, redirects, traversal, duplicates, malformed archives and changed
or unsupported executable bytes.

Eight fresh signature/SBOM checks with the separately verified Windows build
of 2.106.0 passed for the unchanged wheel, sdist, Delta kit/receipt and worker.
The [verification summary](research-candidate-fdfcc19-update-20261126/provenance-verification.json)
links the eight original CLI JSON outputs. Its numeric repository/owner,
source/ref, signer workflow, GitHub-hosted trigger/run, verified timestamp and
signed-SBOM equality policies remain explicit. This is fresh verification of
existing bytes; earlier observations retain their historical identities.

All supplemental data has its own
[checksum set](research-candidate-fdfcc19-update-20261126/SHA256SUMS). The
original packet and November 20 supplement are unchanged. Neither this update
nor the patched verifier grants independent operator or publishing acceptance.
