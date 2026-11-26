# Candidate follow-up: 2026-11-20

This supplements the [original candidate packet](RESEARCH_CANDIDATE_FDFCC19.md).
It preserves that packet's measurements and the exact `fdfcc19` source, wheel,
image, lock, consumers and numerical auditor. Normal Codeowner adoption of the
M0 packet is still pending in [#145](https://github.com/kirchherr/TUC/pull/145).
No independent M1 operator is assigned, and no package has been published.

## Fresh scan of the unchanged image

The [raw scan](research-candidate-fdfcc19-update-20261120/worker-vulnerability-scan.json),
[automated triage](research-candidate-fdfcc19-update-20261120/image-security-triage.json)
and [subsequent assessment](research-candidate-fdfcc19-update-20261120/assessment.json)
bind the actual frozen OCI archive `3ab4ade8…` and config `e860fa50…`.
Trivy 0.76.2 scanned its verified OCI layout without running the image. The
database was updated at 2026-11-20 07:09:47 UTC and downloaded at 09:36:41 UTC;
the assessment records its digest and expiry. No finding suppression was added.
The triage's pending-review field describes the automatic scan stage; the
separate assessment records the subsequent maintainer/AI-assisted review.

| Advisory/package matches | 2026-11-16 | 2026-11-20 |
| --- | ---: | ---: |
| Critical | 2 | 2 |
| High | 100 | 99 |
| Medium | 142 | 142 |
| Low | 108 | 110 |
| Unknown | 5 | 12 |
| Total | 357 | 365 |
| Matches with an available fix | 0 | 0 |
| Python-package matches | 0 | 0 |

These count advisory/package matches, not distinct CVEs or demonstrated exploits.
The database added 17 matches, removed nine and changed classifications/statuses;
the machine-readable assessment lists each change. Removed database matches are
not package fixes: the image bytes are unchanged. The two critical matches and
their [original scoped dispositions](research-candidate-fdfcc19/residual-image-review.json)
remain visible.

The new entries concern glibc encoding conversion and glob cleanup, OpenSSL
PEM/DANE/DTLS handling and GnuTLS certificate/PSK cleanup. The assessment links
the primary advisories. Static review of the fixed worker closure identifies
no user-selected encoding, iconv/glob/POSIX-regex/wide-scanf call, TLS/certificate
import, external connection or command dispatch. Bounded strict UTF-8 input,
fixed imports and the existing isolated runtime controls remain the basis for
this limited reachability inference. This is not a general vulnerability-free
or production approval. The source-converter base/pip profile retains its
separate prior assessment; this update does not claim to rescan that profile.

## Offline review of returned model observations

The [reviewer command](../SUPPLIED_CANDIDATE_OPERATOR.md#offline-packet-consistency-check)
checks twelve fixed JSON files, their candidate/material bindings, all three
original numerical audits and the session/CLI lifecycle claims. The retained
[fresh offline audit](research-candidate-fdfcc19-update-20261120/supplied-wheel-offline-audit.json)
passed against the unchanged project-controlled packet from run `43832760341`.
It records the twelve input digests and reruns eighteen scalar/four-control
checks per consumer without importing TUC or executing the native model.

Passing this data audit cannot authenticate the producer, actual wheel use,
command origin or independent environment control. Both external-origin and
independent-acceptance flags remain false. The supplied-wheel CI workflow now
also checks its freshly produced packet and retains that separate result.

The new security measurements, assessment and offline audit have their own
[checksum list](research-candidate-fdfcc19-update-20261120/SHA256SUMS). The
original packet's checksum list and raw observations remain unchanged.
