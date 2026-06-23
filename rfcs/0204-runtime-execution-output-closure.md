# RFC 0204: Runtime Execution Output Closure

Status: Accepted

## Context

Runtime Execution Receipt v0 and Runtime Execution Evidence Bundle v0 already
linked trusted execution metadata, tensor-store evidence, input/output manifests,
and reference correctness. Runtime Output Contract v0 and Runtime Public Output
Bundle v0 existed as separate proof slices. That left a review gap: a receipt
proved the internal execution evidence but did not directly bind the public
output boundary that callers observe.

## Decision

Runtime Execution Receipt v0 now requires two additional evidence links:

- `output_contract`
- `public_output_bundle`

Runtime Execution Evidence Bundle v0 now embeds those two reports and verifies
that the receipt links match their graph names, contracts, metadata digests,
item counts, pass status, and raw-value policy. Runtime Evidence Gate builds a
proof-of-execution-specific output contract and public output bundle so the
execution receipt is not accidentally bound to the multi-output demo fixture.

## Security Boundary

The closure remains data-only. It serializes metadata digests, graph names,
contracts, item counts, pass/fail status, and raw-value policy. It does not
serialize tensor values, source text, commands, paths, generated artifacts,
backend binaries, device identifiers, environment variables, network targets, or
plugin entry points.

## Consequences

Reviewers can now follow one closed proof chain from trusted execution through
internal runtime value records to the public output contract and read-only public
output bundle. This strengthens the research claim without asserting native
performance, hardware endorsement, cryptographic attestation, or general source
parser completeness.
