# Retained model CLI and session observations at 3324f72

These are actual project-controlled observations from merged source
`3324f72390c3e5711f1be519fa400dfe906df621`, retained on 2026-11-12.
The [installed job](https://github.com/kirchherr/TUC/actions/runs/43265683372/job/131348478082)
passed 552 selected tests, the operator/session/CLI experiments and numerical
audits. The files below are copied directly from the downloaded artifact ZIP
members; no observation was regenerated from expected values.

| Artifact | GitHub ID | ZIP bytes | ZIP SHA-256 |
| --- | --- | --- | --- |
| `bounded-model-application-cli-receipt` | `13965228637` | 2198 | `707393023e2c25de14fbba5b466e0a7c021135258d71ad352a3603db1c6ab09e` |
| `bounded-model-application-session-receipt` | `13966107920` | 2266 | `72cf7a48f6054086fd6e64f247919fe43c2e83f632e6d9a98d623be2ab114e20` |

The artifacts expire on 2026-11-26. The committed JSON members preserve the
observations beyond that retention window. These ZIP hashes identify the
original wrappers, which are distinct from the member hashes below.

| Retained file | Bytes | Member SHA-256 |
| --- | --- | --- |
| [CLI CI packet](bounded-model-application-cli-3324f72-ci.json) | 7268 | `367e605819c77a42e1eb488fca40f000f49ab405296656d5ec1029ec6583d0b2` |
| [CLI observation](bounded-model-application-cli-3324f72-observation.json) | 255 | `ac739bebc07690e3006a4898707992b4f86a1e51704230437e05192cec224c22` |
| [Session CI packet](bounded-model-application-session-3324f72-ci.json) | 7268 | `f219417e889781f93eea24dfa4e78083ce8eecfee3b414ddfc4e5298e40f3484` |
| [Session observation](bounded-model-application-session-3324f72-observation.json) | 347 | `60bf225bc984d8cfbf48c071345b041bb94d371933927cb016bc500414afccec` |

Both packets bind that source and the actual installed wheel SHA-256:
`fd70eef57be9636c67381ee104244fb62848afafefc2df6525a9dce76d653b5f`.
Their consumer hashes match the Git blobs of
`integration/bounded_model_cli/consumer.py` and
`integration/bounded_model_application/native_session_consumer.py` at that
source respectively. Both auditor hashes match the unchanged
`integration/bounded_model_application/audit_native_receipt.py` at that source.

Both numerical records retain the original inner SHA-256:
`6a77307516b633d45b45f8efa4581076c854549491960652026b7219a3ff8bd8`.
From a trusted checkout, repeat the numerical verification with Python alone:

```sh
python -I -S integration/bounded_model_application/audit_native_receipt.py --ci-packet \
  docs/evidence/bounded-model-application-cli-3324f72-ci.json
python -I -S integration/bounded_model_application/audit_native_receipt.py --ci-packet \
  docs/evidence/bounded-model-application-session-3324f72-ci.json
```

Each audit passes eighteen scalar comparisons and four original rejection
controls with `tuc_imported=false` and `native_execution_performed=false`.
The CLI observation records three successes, seven rejected commands, batch
sequences `[1,2]`, single sequence `1` and clean workspaces. The session
observation records two builds, four native calls, three successes, sequences
`[1,2,1]`, closed-session rejection and clean workspaces.

The auditor verifies numerical and identity consistency of the packet. The
additional lifecycle counts and execution origin remain observations tied to
the trusted source and linked job; they are not authenticated by arbitrary JSON.
These files establish same-project reproducibility readiness. Independent
organizational acceptance remains open under the [completion plan](../PROJECT_COMPLETION_PLAN.md).
