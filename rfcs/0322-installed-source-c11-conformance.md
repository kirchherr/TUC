# RFC 0322: Installed Source Intent C11 Conformance

Status: implemented; acceptance requires observed conformance CI and owner review.

## Problem and decision

RFC 0321 exposes bounded compilation to installed applications. Its standalone
consumer validates source artifacts and simulates their schedules, but does not
execute the generated primitives. RFC 0320's older native evidence covers other
fixed graphs; it cannot establish execution of this application's eleven tensors.

Add one standalone CPU conformance client under `integration/bounded_source_c11`.
It constructs the same seven-operation application through the public installed
compiler API, revalidates the complete result, and generates a closed C11 test
context. An explicit shell operator builds and executes that context in isolated
containers. The public compiler API remains an inert artifact producer.

The application has four inputs, three Matmuls, two ReLUs, two row Sums and two
named public returns. Its CPU plan has eleven host slots, thirteen events,
336 planned buffer bytes and no transfers. Tests compare its source and backend
digests, public I/O order and primitive source with the original RFC 0321 client.
There is no independent hand-written implementation of the compiled arithmetic.

## Installed boundary

CI builds a wheel with the existing hash-pinned Python toolchain. A separate
environment installs that wheel. The client and its reviewed support files are
copied outside the checkout and run with Python `-I`; CI verifies that TUC imports
come from the installation and that the checkout is absent from `sys.path`.

The client needs a `wheel-sha256.txt` sidecar containing the digest of the exact
installed wheel. Its context binds that value, the client/oracle source, imported
compiler sources, Source Intent, backend capabilities, public bindings, emitted
artifacts and build/isolation scripts. Accept-time validation reconstructs the
context and rejects drift. The sidecar and receipts are local evidence data,
not an authenticated attestation of installation or execution.

Every native receipt, including the invalid-invocation control, prints a compiled
binding digest over the context inputs. The digest excludes the resulting worker
text to avoid a cycle; the included client source binds its generation logic.
Acceptance requires that digest to match the freshly reconstructed context,
rejecting old receipts mixed with a changed wheel, source or build script.

## Numerical and execution contract

The three fixed corpora contain dyadic values, rounded non-dyadic values and
signed zeros. An independent scalar Python oracle evaluates the application
mathematics without reading compiler operations or schedule events. Multiplication
and addition round separately to binary32. Every intermediate value must be normal
or zero; NaN, infinity and subnormal results are outside this fixed contract.
Numerical equality treats positive and negative zero as equal.

The compiled worker uses the revalidated CPU schedule and explicit public output
bindings. It owns distinct, exactly sized storage, poisons it between replays,
checks input readiness and every output scalar, and checks both publications.
It requires x86-64/SSE2, binary32 evaluation, round-to-nearest, disabled FTZ/DAZ,
`-ffp-contract=off` and `-fno-fast-math`.

Each static and ASan/UBSan baseline must complete three corpora twice: six runs,
42 primitive calls, 36 terminal scalar comparisons and twelve publications.
Thirteen separately compiled mutants exercise seven skipped operations, two
corrupted outputs, two omitted publications, swapped same-shaped returns and
an unwritten final output scalar. Every mutant must reject all six runs with
the specified reason and exact partial counters. An extra command-line argument
must reject before arithmetic. There are thirty receipts across both builds.

## Trust boundaries and isolation

The Python client emits and validates bounded text only. It does not import
plugins, call subprocesses, load native libraries or discover devices. The C
worker has no source/graph/tensor parser or runtime selector: its graph, corpus,
oracle values, dispatch and fault selector are compiled into the executable.
No new native deserializer is introduced.

Emission creates a fresh private directory with an allowlisted context. Receipt
reads are byte/depth/item bounded, reject duplicate JSON keys and non-finite
numbers, and require exact field types and counts. Symlink/path escape and
context changes reject. Synthetic expected receipts are protocol fixtures and
never constitute observed execution.

The operator uses the existing digest-pinned GCC image, a minimal Docker context,
offline build commands, a scratch static stage, and a separate sanitizer stage.
Static binaries must have no dynamic interpreter or needed libraries. Execution
has no network, mounts, devices, capabilities or writable root filesystem; it
runs as a non-root user with default seccomp, no-new-privileges, time, memory,
process, CPU and file limits. A timeout, crash, sanitizer abort or Docker failure
cannot satisfy a negative control's required exit status. CI has read-only
repository permissions and retains the verified aggregate receipt.

## Claim limits

This is one explicit CPU conformance exception for an installed application.
It does not admit caller-controlled runtime graphs, inputs or executable plugins.
It does not establish CUDA execution, CPU/GPU equivalence for this application,
arbitrary-input correctness, independent reproduction, performance or production
sandboxing. RFCs 0319/0320, their workers and earlier physical evidence remain
unchanged. No dev001 connection or reuse of a prior GPU approval is involved.

Owner review and observed CI success are required before accepting this slice.
