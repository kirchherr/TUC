# RFC 0321: Public Bounded Source Intent Compiler

Status: implemented; local validation passed; owner review and CI pending.

## Problem and decision

RFCs 0319 and 0320 established reusable DAG artifact generation and observed
execution of a fixed portfolio. External applications still had to compose
frontend conversion, planning and lowering themselves. That composition also
exposed the broader frontend and planner contracts before the native artifact
compiler's tighter limits could reject an input.

Add an explicit, data-only facade in `tuc.compiler.bounded_source`:
`compile_bounded_source_intent(module, backend_bindings)`. It validates the
complete smaller contract first, snapshots caller data, converts it with the
existing Source Intent metadata adapter, invokes the existing compiler's
capability-based planner and lowers the resulting HAC-IR/partition through
RFC 0319. It returns the existing compilation result, source artifacts,
public input/output bindings and separate source/capability digests.

This is an API for installed external consumers. SourceIntentModule remains a
passive data model; this separate entry point explicitly requests compilation.
No new source parser, backend plugin protocol, executable loader or runtime
registration is introduced. Generated C11/CUDA remains in-memory source text.

## Accepted input and validation order

Accept exact known Source Intent data classes, tuples and primitive values.
Require static dense FP32 tensors of rank one or two with dimensions 1–64;
at most eight operations, 24 tensors and one million scalar arithmetic steps.
Names are bounded to 64 ASCII identifier bytes. Supported semantics are
rank-two Matmul, explicit ReLU and row Sum with `axis=1`. Operation arity,
shapes, global SSA, definition-before-use and complete used tensor declarations
are checked before metadata conversion. There must be explicit required public
returns covering every terminal tensor exactly once, with distinct aliases.

Only the existing finite, bounded neutral hints are accepted. Neither hints nor
capability declarations establish a numerical error guarantee. Metadata and
artifact budgets remain those of RFC 0319; exact residency storage/event limits
are enforced after planning, before emission completes.

Accept one or two `BoundedBackendBinding` records with unique names and targets.
Each associates a static `BackendCapability` with the closed `DAGTarget` enum.
Validate every field and reconstruct ordinary capability instances before
planning. Row-major layouts are required. C11 maps to `HOST_RAM`; CUDA sm86
maps to `UNKNOWN`, preserving the existing distinction between accelerator
address space and a claimed physical memory technology. Binding input order is
canonicalized by backend name. Unused capabilities remain bound and inspectable
but are omitted from the selected lowering target map.

Every selected assignment must be covered by its declared capability. Reject
the planner's fallback reason even if the fallback name matches a supplied
backend. Do not expose manual assignment overrides through this facade.
Planner reasons, candidates, transfers, HAC-IR and HS-IR remain available in
the existing `CompilationResult`. No additional hierarchy of admission reports
is introduced.

## Data trust boundary

Exact types prevent subclass dispatch; size checks precede iteration and
serialization. Source Intent stores hints and attributes in mapping proxies.
The new boundary accepts a proxy only when bounded `gc.get_referents` inspection
identifies one exact backing `dict`; it then reads that plain dictionary.
Proxy wrappers around arbitrary mappings, unsupported referent representations
and additional instance fields fail closed. This conservative representation
check is exercised on CPython; unsupported implementations may reject.

The facade reconstructs its validated inputs before invoking existing methods.
It does not call instance-supplied capability hooks, formatting or comparison
methods. Diagnostics use bounded generic rejection text instead of interpolating
untrusted input. Python callers already execute Python; these checks constrain
the compiler boundary and do not sandbox the surrounding Python process or
concurrent mutation by another thread.

## Result and revalidation

`BoundedSourceCompilation` contains `compilation`, `artifacts`, `input_bindings`,
`output_bindings`, `source_intent_digest` and `backend_bindings_digest`.
Each `BoundedTensorBinding` provides public/tensor names, manifest tensor index,
shape and dtype. Inputs use their tensor names; outputs preserve the explicit
public return order and aliases. Canonical source and capability digests also
bind unused capabilities; the artifact manifest retains its existing semantics.

The result container and source texts are frozen. The existing compilation
contains mutable metadata dictionaries, so the whole object is not deeply
immutable. `validate_bounded_source_compilation(module, backend_bindings, result)`
reconstructs a fresh expected result and checks bounded, exact-type fields
against it. It rejects source, capability, decision, metadata, I/O and artifact
drift without calling methods or equality hooks on untrusted nested objects.
Validation is deterministic metadata verification, not physical provenance.

## Installed consumer and evidence

`integration/bounded_dag_compiler` is a standalone client using only public
installed TUC APIs. Its seven-operation graph combines three Matmuls, two ReLUs
and two row Sums, with four external inputs and two public outputs. It is not
one of RFC 0320's fixed native graphs. Three capability sets select CPU, CUDA
or mixed placement automatically while source intent, HAC-IR, public returns
and arithmetic source stay identical.

Tests compare a separate binary32 reference with manifest buffer/event replay,
exercise malformed source and backend metadata, and mutate the returned
artifacts/decisions. A dedicated read-only CI job builds the wheel using the
existing hash-pinned toolchain, installs it in a separate environment, copies
the standalone client outside the checkout and runs Python in isolated mode.
It verifies installed imports and the exact deterministic consumer report.
This workflow compiles Python packaging only; it never compiles or executes
generated C11/CUDA and performs no remote-host connection.

## Preserved boundaries

The RFC 0319/0320 compiler, generators, native workers, workflow bindings and
original evidence stay byte-for-byte unchanged. New source graphs acquire no
native execution approval from this API or the old matrix. Arbitrary-input
numerical correctness, dynamic shapes, broader operators/targets, performance,
parallel execution and ordinary native runtime admission remain open.
Any later dev001 payload needs its own source-bound review and authorization.
Normal owner review and CI gates apply before integration.
