# RFC 0152: Source-To-Intent Corpus Evidence

## Status

Accepted.

## Context

RFC 0151 made the first Source-to-Intent parser proposal visible as research
readiness evidence. It also showed that accepted and rejected source corpus
evidence was still missing.

Before implementing parser logic, TUC needs explicit source-buffer fixtures that
define what a future parser must accept and reject. This keeps the research
path falsifiable and avoids building parser behavior around unstated examples.

## Decision

Add Source-To-Intent Corpus Evidence:

```text
examples/source_to_intent_corpus.py
tests/corpus/source_to_intent_parser/
tests/golden/frontend/source_to_intent_corpus_report.json
docs/SOURCE_TO_INTENT_CORPUS.md
```

The current accepted fixtures cover all MVP operation families:

```text
elementwise,matmul,reduction,softmax
```

The current rejected fixtures cover:

```text
ambiguous_softmax_axis
decorator_call
hardware_specific_source_hint
import_statement
```

The research readiness example now marks `accepted_source_corpus` and
`rejected_source_corpus` as present. Parser fuzz/property evidence and parser
report golden evidence remain missing.

## Security Boundary

This change does not add source parsing, source-to-intent conversion, source
file loading as compiler input, Python imports, decorator evaluation,
`@triton.jit` execution, bytecode compilation, frontend module inspection,
plugin discovery, backend discovery, device access, network access, subprocess
execution, generated artifact execution, direct `ComputeGraph` construction
from source, or any source-to-metadata shortcut.

The corpus report serializes only case IDs, expectations, byte counts, source
digests, operation-family labels, expected rejection labels, and blocked
execution/compiler-output labels. It does not serialize raw source text.

## Consequences

TUC now has accepted and rejected source corpus evidence for the first narrow
parser proof while the parser remains blocked. Later RFCs add parser
fuzz/property obligations and a proposal-only parser report golden.
