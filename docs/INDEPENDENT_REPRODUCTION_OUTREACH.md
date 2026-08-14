# Independent Reproduction Outreach

TUC is seeking one independent person or organization to reproduce the fixed
Objective Delta experiment released with TUC v0.1.0. The public request is
tracked in [GitHub issue #85](https://github.com/kirchherr/TUC/issues/85).

This outreach has one success criterion: a publicly reviewable reproduction
performed under an identity and CI environment outside `kirchherr/TUC`.
Repository stars, page views, endorsements, and general project reviews are not
substitutes for that evidence.

## Canonical Links

- Reproduction request: [GitHub issue #85](https://github.com/kirchherr/TUC/issues/85)
- Immutable release: [TUC v0.1.0](https://github.com/kirchherr/TUC/releases/tag/v0.1.0)
- Reproduction contract: [Objective Delta Reproduction Kit](OBJECTIVE_DELTA_REPRODUCTION_KIT.md)
- Installed proof boundary: [Objective Delta Installed Portable Compute](OBJECTIVE_DELTA_INSTALLED_PORTABLE_COMPUTE.md)
- Package: [`tuc==0.1.0` on PyPI](https://pypi.org/project/tuc/0.1.0/)

## Who Can Reproduce It

The task is suitable for a compiler engineer, research software engineer,
reproducibility researcher, advanced student, or open-source maintainer. It
requires approximately 20-30 minutes, a clean Linux environment, CPython 3.11
or 3.12, and no GPU or accelerator.

The reproducer does not need to endorse TUC, review the complete architecture,
contribute code, or accept any performance claim. A failed reproduction is
useful when the environment and failure evidence remain public and bounded.

## Forum Post

Use this version for a technically relevant compiler or reproducibility forum.
Adapt the first sentence to the community and post in only one appropriate
category.

```text
Independent reproducer wanted for a bounded universal-compute experiment

TUC is an open research prototype testing whether one fixed compute intent can
be planned across data-described backend capabilities, executed by trusted
prototype backends, and checked against deterministic reference semantics.

We are looking for one independent person or organization to reproduce the
Objective Delta v0.1.0 experiment in infrastructure outside the TUC repository.
The task is deliberately small: CPU only, CPython 3.11 or 3.12, approximately
20-30 minutes, no repository checkout, and no execution of source supplied by
the reproduction kit.

The released data-only kit is checksum-bound and covered by GitHub artifact
attestations. A successful run produces a deterministic metadata-only receipt.
A failed run is equally welcome when its environment and bounded diagnostic are
reported.

Scope: this tests one published semantic experiment. It does not claim native
backend support, physical-device execution, performance parity, arbitrary
source ingestion, or replacement of existing compiler stacks.

Reproduction request and exact acceptance criteria:
https://github.com/kirchherr/TUC/issues/85

Release:
https://github.com/kirchherr/TUC/releases/tag/v0.1.0
```

## Direct Message Or Email

Use this for a small number of individually selected researchers or engineers.
Personalize the opening with a concrete reason their work is relevant.

```text
Subject: Independent reproduction request for a bounded compute-portability proof

Hello <name>,

I am looking for one independent reproduction of Objective Delta in TUC, an
open research prototype for a hardware-independent compute interface. I am
contacting you because of your work on <specific relevant topic>.

This is not a request for endorsement or a broad architecture review. It is a
fixed 20-30 minute CPU-only experiment using the immutable TUC v0.1.0 release.
The reproducer verifies release checksums and attestations, installs
tuc==0.1.0, executes a data-only kit in independently controlled infrastructure,
and publishes the deterministic metadata-only receipt. No repository checkout,
GPU, external backend code, or source execution is required.

The exact procedure, claim boundary, and evidence requested are here:
https://github.com/kirchherr/TUC/issues/85

A failed reproduction is also valuable. Please feel free to decline; I will not
send follow-up messages unless you express interest.

Regards,
Tobias Kirchherr
```

## Short Public Post

```text
Independent reproducer wanted for TUC Objective Delta v0.1.0: one bounded,
CPU-only universal-compute experiment, about 20-30 minutes, with a data-only
release kit, attestations, and a deterministic metadata-only receipt. This is a
reproducibility request, not a performance or vendor-replacement claim.
https://github.com/kirchherr/TUC/issues/85
```

## Target Channels

Use narrow, technically relevant channels before broad social distribution.
Read each community's current rules and obtain moderator guidance when project
promotion is unclear.

1. **Direct research outreach.** Contact five to eight people whose published
   work concerns compiler reproducibility, heterogeneous compilation, MLIR,
   runtime evidence, or artifact evaluation. Use public professional contact
   channels and personalize every request.
2. **LLVM Discourse, MLIR category.** Frame the post as a bounded external
   reproducibility request and ask for methodological criticism. Do not imply
   that TUC is an LLVM or MLIR project.
   <https://discourse.llvm.org/c/mlir/31>
3. **Apache TVM Discuss.** Use a relevant development or questions category
   only after checking the forum rules. Explain that no comparison with TVM is
   being claimed and do not cross-post into multiple categories.
   <https://discuss.tvm.apache.org/>
4. **PyTorch Developer Mailing List, compiler category.** Use only when the
   post is framed around reproducibility of compiler/runtime evidence rather
   than general project promotion.
   <https://dev-discuss.pytorch.org/c/compiler/5>
5. **OpenXLA community discussions or mailing list.** Present Objective Delta
   as an independent research experiment and avoid suggesting affiliation.
   <https://github.com/orgs/openxla/discussions>
6. **Professional networks.** Publish the short post through the maintainer's
   existing LinkedIn, Mastodon, university, or professional contacts after the
   targeted requests are underway.

Do not bulk-message maintainers, scrape personal addresses, automate outreach,
or repeat the same post across unrelated communities.

## Fourteen-Day Sequence

| Day | Action | Evidence to retain |
| --- | --- | --- |
| 0 | Publish the canonical GitHub issue and repository links | Issue URL and release URL |
| 1-2 | Send five to eight personalized direct requests | Count only; keep private correspondence private |
| 3-5 | Publish one forum post in the most relevant community | Public post URL |
| 7 | Publish the short post through existing professional networks | Public post URL |
| 10 | Send one follow-up only to people who expressed interest | No private content in the repository |
| 14 | Review responses, traffic, clones, and reproduction attempts | Public links and aggregate counts |

Pause new direct requests when one qualified reproducer commits to the task;
resume only if that person withdraws or the agreed attempt does not proceed.
The target is met only by a completed, publicly reviewable result. Additional
independent results are welcome, but creating pressure or competing requests
would weaken the research relationship.

## Independence And Disclosure

A result can be considered for independent evidence only when the reproducer:

- controls the repository and CI identity that produce the receipt;
- uses unmodified v0.1.0 package and release artifacts;
- does not run from `kirchherr/TUC` infrastructure;
- discloses prior TUC contributions, close collaboration, or compensation; and
- permits the public evidence links and digests to be cited by TUC.

Compensation for time does not automatically invalidate a result, but it must
be disclosed and the reproducer must retain control of execution and reporting.
An undisclosed or maintainer-operated run remains maintainer evidence.

## Response Handling

Keep outreach and evidence review separate. Before recording a result:

1. verify the external repository owner, exact commit, and public workflow run;
2. verify the release checksums and both GitHub artifact attestations were
   checked by the external workflow;
3. verify the generated receipt digest and byte comparison;
4. inspect the receipt and workflow artifact without requesting environment
   dumps, credentials, host paths, device identifiers, source payloads, or raw
   tensor values;
5. record PASS or FAIL with the reproducer's disclosed relationship to TUC; and
6. obtain consent before naming or quoting the reproducer in project docs.

Do not silently repair an external run in maintainer-controlled infrastructure.
Document the problem, let the reproducer decide whether to retry, and preserve
the distinction between external and maintainer evidence.

## Measurement

The primary metric is `qualified_external_reproductions`, with a target of one.
Supporting metrics are public responses, committed reproducers, completed
attempts, and public evidence links. Traffic, clones, stars, and reactions are
diagnostic only and must not be presented as proof of research validity.
