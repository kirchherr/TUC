# Project completion review and delivery plan

Reviewed on 2026-11-12 against merged engineering baseline
`3324f72390c3e5711f1be519fa400dfe906df621` (RFC0342, PR #140).
Decision: [RFC0343](../rfcs/0343-acceptance-led-roadmap.md).

Updated on 2026-11-13 with the normally merged #143 source `8044760`, its
[protected engineering dry-run and retained evidence](evidence/RESEARCH_CANDIDATE_8044760.md).
Security findings from the actual image require the current refresh and a new
candidate pin; the successful dry-run is not the M0 freeze.

## What completion means

The next deliverable is a reviewed **bounded CPU model research release**:

```text
model + explicit capabilities -> portable bundle -> exact request
    -> isolated CPU execution -> checked public output bits
```

It includes the existing Python APIs, reusable build sessions and installed
`tuc-model-app` single/batch interface. Existing static FP32, graph, shape,
request and cumulative budgets define its scope. C11/CUDA/mixed source planning
remains available; this runtime admits only the existing all-C11 Linux x86-64
boundary. The capability and planning contracts stay hardware-neutral.

This deliverable is accepted when M0, M1 and M2 below are complete. The larger
TUC mission remains active through independent backend integration, distinct
physical portability evidence, separately governed performance work and an
accepted organizational pilot. A
bounded release does not grant production source, plugin or general native
backend admission.

## Review findings

This is a maintainer/AI-assisted review of the model CLI, backend declaration
decoder, session lifecycle, original-context validation, retained observations,
CI results and planning/governance documents. The reviewed source boundaries
preserve validation before execution, closed targets, cumulative budgets,
per-request identity and cleanup before result publication. No new blocking
runtime defect was identified in this scope.

| ID | Severity and finding at the baseline | Disposition |
| --- | --- | --- |
| R1 | P2: Roadmap entries describe merged RFC0341/0342 as candidates with validation still delegated to the PR; implementation status and independent acceptance are not separated. | Corrected with merge/source evidence and explicit open acceptance state. |
| R2 | P2: The priority list mixes maintenance, older completed increments and future research without an ordered release completion test. | Replaced by M0-M6, owners, dependencies and required exit artifacts. |
| R3 | P2: New CLI/session observations are retained in 14-day CI artifacts; the existing offline kit retains the older original numerical observation. Rebuilding that kit cannot recreate the actual new lifecycle observation. | Four actual baseline JSON files are retained byte-for-byte with artifact/source bindings and offline audits in the [evidence index](evidence/BOUNDED_MODEL_APPLICATION_3324F72.md). |
| R4 | P1 for release readiness: effective `main` rules enforce PR review, deletion and non-fast-forward protection, but omit `required_status_checks` and linear-history enforcement required by the documented branch policy. | Resolved. Owner-approved ruleset `17319611` enforces strict Actions-bound required checks, linear history, Squash/Rebase and Codeowner review, with no bypass actors. #143 merged normally; actual rule suite `5098619497` passed all five evaluations. |
| R5 | P2: The only listed codeowner is `@kirchherr`, also author of the recent PRs. The active rule requires one codeowner approval; technical self-comments did not satisfy it, and #139/#140 used separately authorized exceptions. | Resolved. The owner's selected Write-enabled Codeowner `mailactiveblue-blip` formally approved #143's exact final head. The ordinary Squash merge passed the active rules without bypass. Consumed exceptions confer no future permission. |
| R6 | P1 for candidate freeze: the attested engineering worker still uses the older Python/OS image; its actual scan has vendor-fixable package findings. BuildKit 0.30.0 also matches two published advisories. | Security refresh prepared: current fixed Linux/amd64 Python base, a separate research Dockerfile/SBOM for the existing six-module closure, dependency/installer removal, and BuildKit 0.35.0. Actual context-exclusion and client-entitlement probes supplement configured policy. Merge validation, rebuilt-image scan, residual-finding review and a new protected candidate run remain required. |

R4/R5 are verified through the ordinary #143 merge. The owner-approved tag,
alert and PyPI environment controls were also read back on 2026-11-13: required
reviewers, no self-review, no administrator bypass and unchanged deployment
filters. The separately approved historical publisher retirement was also
verified: its Actions state is `disabled_manually`, while CI and the candidate
workflow remain active. R6 and the M0 freeze remain open. Consumed merge exceptions
confer no future permission.
The observed effective-rule endpoint was
`GET /repos/kirchherr/TUC/rules/branches/main`, backed by active ruleset
`17319611`. The verified controls now enforce the
[branch protection policy](BRANCH_PROTECTION.md).

## Evidence already available

- The [#143 dry-run evidence](evidence/RESEARCH_CANDIDATE_8044760.md) records the
  successful normal Codeowner path, two 7,771-test main/candidate suites,
  552 installed-model tests, actual retained core/session/CLI JSON, candidate
  checksums and eight fresh signature/SBOM checks. The CI and candidate wheels
  have distinct hashes. Image security findings supersede `8044760` for the
  freeze; current refresh code needs its own source/artifact validation.
- [PR #139](https://github.com/kirchherr/TUC/pull/139) merged reusable model
  application sessions; [PR #140](https://github.com/kirchherr/TUC/pull/140)
  merged the installed CLI. The latter's reviewed tree and PR test-merge tree
  equal the merged baseline tree.
- Both final #140 suites passed 7,768 tests with two skips, Ruff, strict Mypy
  for 169 source files and their subsequent proof gates:
  [branch regression](https://github.com/kirchherr/TUC/actions/runs/43258076800/job/131321624396),
  [PR regression](https://github.com/kirchherr/TUC/actions/runs/43258203553/job/131322068838).
- The [merged-source installed job](https://github.com/kirchherr/TUC/actions/runs/43265683372/job/131348478082)
  passed 552 selected tests, three CLI results, seven CLI rejection controls,
  the two-build session experiment and the unchanged numerical audit.
- The [baseline main regression](https://github.com/kirchherr/TUC/actions/runs/43265683017/job/131348475862)
  also passed 7,768 tests with two skips, Ruff, strict Mypy and all subsequent
  gates. All 33 baseline main checks completed: 31 successes, two expected
  skips, no failures. CI conclusions apply to that exact revision.
- Project-controlled replay and CI establish engineering reproducibility.
  Independently controlled reproduction has not been supplied for this model
  path. The published Objective Delta v0.1.0 experiment and
  [its reproduction issue](https://github.com/kirchherr/TUC/issues/85) are a
  distinct scope; one experiment's result cannot silently close the other.

## Milestones

The ordering below governs the next work. Owner roles describe required
responsibility; an external operator or author has not yet been assigned.

| ID | Outcome and owner | Required exit artifact | Current state |
| --- | --- | --- | --- |
| M0 | Prepare and freeze the next research release candidate. Maintainer and repository owner. | No unresolved blocking findings; actual branch/review/publishing controls verified; version/support scope and exact source, lock, wheel, image and verifier identities recorded; exact-revision required CI passed. | Four protections and normal Codeowner path verified; legacy publisher disabled with approval; 0.2.0 engineering dry-run and signature checks passed. R6 security refresh, actual updated-image scan/residual review and a new protected candidate pin remain open. |
| M1 | Reproduce the frozen candidate outside project control. Independent operator, reviewed by maintainer. | Attributable fresh core, session and CLI observations, source/wheel bindings, command/run origin and passing offline audits; independence and scope accepted in review. | Open; requires M0's candidate pin and an independently controlled environment. |
| M2 | Publish the accepted bounded research release. Release owner and eligible approver. | Protected exact-source release, wheel/sdist, checksums, SBOM and verified provenance; release notes bind M1's result and state the supported boundary. | Open; requires M0/M1, a reviewed replacement publisher and actual PyPI binding, then normal release/publishing approvals. |
| M3 | Have another developer integrate a data-only backend through the installed contract. Independent backend author. | Author-owned package, negative conformance and inspectable plan, installed reproduction, no TUC core modification. | Open external author milestone; existing Gamma/Delta CI provides the starting contract. |
| M4 | Add a distinct physical portability proof. Hardware operator and compiler/runtime reviewer. | One bounded neutral workload on another vendor or ISA, reviewed source/images/host boundary, correctness and transfer evidence with attributable observations. | Future; existing same-vendor GPU and C11 observations remain their original bounded proofs. |
| M5 | Evaluate performance under a separate accepted protocol. Benchmark/review owners. | Planner overhead, native reference provenance, methodology, repeated measurements and interpretation accepted by the existing performance gates. | Future; performance claims remain gated. |
| M6 | Obtain scoped organizational adoption. Pilot organization, maintainer and applicable security reviewers. | Attributable acceptance for a declared real workload, support/compatibility and operational criteria, reviewed admission boundaries and documented integration effort/risk. | Open long-term goal; an organization and pilot workload have not been assigned. |

M3 author coordination and M6 pilot design can proceed alongside M0-M2. M4/M5 need their own
concrete RFC, hardware availability and source-bound execution authorization.
They do not reopen arbitrary source, plugin or device authority by default.
M6 uses the validated integration/portability results applicable to its pilot;
M5 is required for performance claims or pilot performance acceptance criteria.

## Immediate work: M0

1. Resolve the review findings and keep the accepted numerical corpus, old
   receipts, goldens and proof-bound legacy CI intact. Keep actual current
   observations publicly replayable after CI artifact expiry.
2. Preserve the verified `main`, tag and environment controls. Required
   `python`, `CodeQL` and `Dependency Review` checks, linear history and an
   eligible Codeowner were exercised by #143's normal merge. Future PRs use
   this path; past exceptions are not standing authorization.
3. Review the open dependency/action/image update queue against current
   authoritative security information and compatibility requirements. Resolve
   applicable security findings and validate any lock/pin change separately.
   An available version update alone is not evidence of a vulnerability.
   R6 now has actual image/package and BuildKit advisory evidence. Validate the
   separate research-worker profile and active converter's current base,
   rescan the rebuilt image and assess remaining findings against the fixed
   execution/import/network boundaries. A base-only scan is insufficient.
4. Prepare the next package version and supported-platform statement, complete
   the existing protected release dry-run and verify checksums, SBOM and
   provenance. Verify actual publishing settings against
   [release governance](RELEASE_GOVERNANCE.md) and
   [release security](RELEASE_SECURITY.md).
   Version 0.2.0 and its bounded support statement are prepared in the latter.
   The protected `8044760` dry-run and fresh signature checks passed; it is
   superseded for freeze by R6. The candidate workflow keeps
   distribution builds and the isolated wheel check on a separate reviewed
   research-candidate hash lock. Historical workflow/lock/Dockerfile/SBOM
   materials and their proof remain unchanged. The old publisher has been
   disabled with owner approval. Keep publishing fail-closed until M2's
   replacement and actual PyPI binding are reviewed; create no 0.2.0 tag now.
5. After the refresh passes normal review, repeat the protected candidate run
   and record a single exact candidate revision and artifact identities for M1.
   New source, build inputs, lock, consumer or verifier changes require a new
   reviewed pin and the applicable repeat validation. The baseline `3324f72`
   is the reviewed engineering reference, not an automatically published new
   package version.

During this closure work, accept changes that resolve a review finding,
operator reproduction obstacle or release exit requirement. Put additional
input surfaces, operations, runtime targets and optimization work through the
milestone/RFC that supplies their distinct hardware-independence evidence.

## Independent acceptance: M1

The owner must identify an operator with independently controlled Linux x86-64,
CPython 3.12 and local Docker, and an attributable return channel. Another
same-maintainer VM or project CI run remains project-controlled evidence.
Selecting an operator does not itself authorize outreach or remote execution.

The [operator procedure](../integration/bounded_model_application/README.md)
builds from a committed snapshot using hash-locked dependencies, executes the
fixed native corpus and emits `operator-observation.json`. The
[current handoff](BOUNDED_MODEL_APPLICATION_HANDOFF.md) extends the procedure
with the already implemented session and installed-console experiments.
Use M0's exact candidate pin for formal acceptance; replaying engineering
baseline `3324f72` is also useful, with its original scope stated explicitly.
The existing operator runner builds its own wheel with the historical CI lock.
Formal supplied-candidate-wheel acceptance needs a reviewed procedure that
installs and verifies that exact wheel with the candidate lock, runs the three
existing consumers outside the checkout and retains attributable observations.
Neither a rebuilt CI wheel nor the `8044760` rehearsal supplies this result.

Acceptance requires all of the following in one review:

- Exact source and independently supplied wheel identity, matching the reviewed
  consumer/verifier/build inputs and actual command/run origin.
- Core numerical audit: three fixed contexts, eighteen scalar comparisons,
  four original rejection controls and the original record digest.
- Session observation: two builds, four invocations, three successes,
  sequences `[1,2,1]`, terminal overflow cleanup and closed-session rejection.
- CLI observation: installed execution outside the checkout, batch sequences
  `[1,2]`, single sequence `1`, three successful requests, seven rejection
  controls and clean workspaces.
- Attributable operator/environment control and a retained reviewed result.
  Arithmetic verifiers check consistency and numbers; operator independence
  and execution origin require separate provenance review.

Record discrepancies as reproducible findings. A pass covers the named source,
environment and corpus. A changed release candidate needs explicit scope and
identity review; an old receipt is not automatically evidence for a new source.

## Release and larger goal

M2 requires a reviewed replacement for the disabled historical publisher and
its verified PyPI Trusted Publisher binding. It then uses the exact accepted
candidate after M0/M1 and normal environment approval. Release notes
state that the bounded model path has the recorded external result. They keep
broader source support, executable plugin admission, physical cross-vendor
portability and performance tied to their separate evidence requirements.

The [master plan](../TUC_MASTER_PLAN.md) succeeds when an outside hardware
organization can integrate with less effort and risk than maintaining its own
stack. M3 supplies the next direct integration test of that thesis. Record
onboarding effort, core changes required, capability/plan conformance and
reproduction obstacles. M4/M5 then test physical portability and performance
with their own falsifiable acceptance protocols. M6 records an outside
organization's actual workload, supported interface/platform agreement,
operation/recovery expectations, relevant security/admission review and
integration effort compared with its stated alternative. Its acceptance closes
the organizational-use obligation for that scope; it cannot grant unrestricted
source/plugin/native execution or universal hardware claims.
