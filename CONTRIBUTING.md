# Contributing To TUC

TUC is currently moving through Phase 1. Contributions should focus on turning
the concept into a small, testable, secure compiler and runtime prototype.

## Development Principles

- Preserve Triton-style developer ergonomics.
- Keep the MVP narrow and measurable.
- Prefer explicit IR and backend contracts over implicit behavior.
- Make compiler and runtime decisions inspectable.
- Treat exotic hardware support as simulator-first until real hardware is
  available.
- Keep GPU compatibility as a trust-building baseline.

## Before Opening A Pull Request

Run:

```bash
ruff check .
mypy src/tuc
pytest -q
```

Inside Docker:

```powershell
docker compose run --rm dev bash
```

Then:

```bash
ruff check .
mypy src/tuc
pytest -q
```

## RFCs

Architectural changes should start as RFCs when they affect:

- IR structure or operation semantics.
- Backend API contracts.
- Runtime partitioning behavior.
- Noise-aware tuning models.
- Public developer-facing syntax.
- Governance, release, or compatibility policy.

Use [rfcs/0000-template.md](rfcs/0000-template.md).

## Security Requirements

Compiler and runtime changes must follow
[docs/SECURITY_BASELINE.md](docs/SECURITY_BASELINE.md). Treat source text,
serialized IR, graph metadata, backend capabilities, plugin manifests, and
runtime plans as untrusted until validated. Add negative tests for malformed or
malicious input whenever an input boundary changes.

## Commit Style

Use short, descriptive commit messages:

```text
Add simulator backend capability model
Document Phase 0 architecture
```

## Language

Code, public docs, RFCs, and GitHub-facing material should be written in English.
German planning notes are fine for internal exploration.
