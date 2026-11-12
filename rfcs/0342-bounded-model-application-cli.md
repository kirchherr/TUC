# RFC 0342: Portable Model Application CLI

- Status: Implemented and merged in PR #140; independent acceptance remains open
- Date: 2026-11-12
- Depends on: RFCs 0325, 0330, 0333, 0337, 0338, 0340, 0341

## Problem and decision

The portable model path requires applications to construct Python capability
objects, serialize bundles and requests, and connect the explicit runtime.
Expose one installed `tuc-model-app` command for that complete existing path.
Hardware declarations remain data; the planner determines placement without
fallback before any native authority is requested.

`plan`, `inspect` and `request` only validate data and return a bundle,
metadata or request. `run` requires the original model, backend declarations,
bundle, concrete inputs and exact request. `run-batch` uses the existing model
batch format, validates its entire expansion and then uses one RFC0341 session.
All results publish together only after successful runtime cleanup.

## Trust boundaries and limits

The new `tuc.bounded_backend_bindings.v0` envelope carries one or two explicit
capability-to-target bindings. Its decoder uses the existing bounded lexical
prepass: at most 64 KiB, depth five and 4,096 tokens; duplicate keys, non-finite
numbers, numeric underflow, invalid UTF-8 and unpaired surrogates reject.
Every field is explicit. Unknown fields, duplicate operations/names/targets,
invalid preferred subsets, layouts, target/domain pairs and budgets reject.
The existing source compiler's snapshot validator owns the final invariants.
The serializer revalidates native Python records without dispatching user hooks.

Planning supports the already accepted C11, CUDA and mixed declarations; these
are inert source targets. Every declared binding must be C11 before execution.
No endpoint, image, command, import, plugin, device or fallback override exists.

File commands reuse RFC0325's Linux x86-64 regular-file boundary: no symlink
components, FIFO/device reads, parent traversal, oversized files or metadata
drift. The CLI writes only complete bounded stdout; native work is confined to
the explicit absolute workspace and existing isolated C11 runtime. Help is inert
on all platforms. Diagnostics are closed, bounded and contain no input or logs.

Model, input, bundle, request and batch byte limits remain unchanged. Before any
runtime import, the batch gate validates all requests, distinct IDs, shared
inputs, fixed-parameter exclusion, at most sixteen requests and separate
65,536-element expanded input/output budgets. Fixed parameters count per call.
A later malformed request executes nothing. A later native or cleanup failure
discards all collected results. No cross-invocation handle persists.

## Evidence and claim boundary

The installed-wheel experiment runs the actual console entry point in separate
processes outside the checkout. It verifies installed-module location, planning,
metadata inspection, exact request creation, two ordered batch results, a
changed-parameter single call, four original rejection controls, a malformed
later batch request, request replay and CPU rejection of a CUDA declaration.
The existing numerical corpus, record format and standard-library auditor are
unchanged; the inner record must retain its original SHA-256 and pass eighteen
scalar comparisons plus four rejection controls.

The outer CLI result reports locally observed execution; each embedded protocol
receipt retains `native_execution_observed=false`. Neither flag authenticates
an arbitrary JSON sender. Project-controlled CI does not supply independent
organizational acceptance, performance evidence or general backend admission.
No existing goldens, original receipts or proof-bound legacy CI are changed.
