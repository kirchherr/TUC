# RFC 0341: Reusable Bounded Model Application Sessions

- Status: Implemented and merged in PR #139; independent acceptance remains open
- Date: 2026-11-12
- Depends on: RFCs 0339, 0340; follows the lifecycle controls of RFC 0334

## Problem and decision

RFC0340 validates and executes one portable model request, then removes its
native resources. Several requests against the same model and bundle therefore
repeat the build. Add an explicit Python session that retains one existing
isolated C11 build for a fixed, fully validated model/capability/bundle context.

The factory and context-manager entry perform only bounded data validation.
The first valid `run(input_data, request_data)` builds. Later valid calls reuse
the same handle and start a fresh isolated native process for each frame.
No process or native parameter state stays resident between calls.

## Invariants

The factory accepts original model bytes, all original backend bindings,
bundle bytes and an absolute workspace path. Every binding must select C11;
CUDA and mixed declarations reject without fallback. The workspace is not
accessed until execution.

Before each process, the session revalidates its original context and the
concrete request. Model, bundle, compilation, capability and program digests
must remain fixed. The existing handle also rechecks its program and owned
Docker context. Responses are decoded against the exact original context and
request, including tensor positions and bit representations.

At most 16 successful requests, 65,536 expanded input elements and 65,536
output elements are allowed per session. Fixed parameters count again on
every request because every native process receives a complete frame. Existing
per-request, Docker, time, output and workspace limits remain in force.

An invalid input or substituted request causes no native action and advances
no counter. Context mutation closes the session. Build, execution or response
failure also closes it before another invocation. Cleanup failure retains the
handle for explicit close retries. Run and close operations cannot overlap;
concurrent operations reject immediately. Construction, subclassing and forged
handles do not create execution authority.

## Results and evidence

A result contains a session-local sequence number and the existing immutable
model application result. Its protocol receipt still records
`native_execution_observed=false`: data consistency is not provenance.
No existing serialized receipt or request contract changes.

The installed CI experiment uses the unchanged numerical corpus and existing
standard-library auditor. Base and variable cases share one build; an
overflow closes that session, and a changed fixed-parameter model uses another.
The observer counts actual Docker build/run commands: two builds, three
successful invocations, one numeric rejection and sequences [1,2,1].
The numerical record must match the retained original record bit-for-bit.
Lifecycle counts are project-controlled observations, not independently
authenticated facts obtainable from a JSON file.

## Scope

This is build reuse at the existing explicit CPU boundary. It adds no parser,
plugin, endpoint/image override, general native backend, persistent cache,
cross-process handle, resident weights, GPU admission or performance claim.
Independent organizational acceptance remains a separate obligation.
