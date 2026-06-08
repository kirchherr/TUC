## Summary

Describe the change.

## Testing

List commands run, for example:

```bash
ruff check .
mypy src/tuc
pytest -q
```

## RFC / Design Impact

Does this change affect IR, backend APIs, runtime behavior, developer-facing
syntax, or governance?

## Proof Artifact Impact

Does this change proof examples, proof metadata, proof golden files, HAC-IR
proof fixtures, runtime-plan proof fixtures, or proof documentation?

If yes, answer the checklist in
`docs/PROOF_ARTIFACT_REVIEW.md`.

## Security Impact

- What input boundary changed?
- What validation or resource budget applies?
- Could this execute code, import modules, spawn processes, load dynamic
  libraries, write files, or expose secrets?
- What malformed or malicious-input tests were added?

## Supply Chain Impact

Does this change CI, dependencies, Docker, release automation, credentials, or
publishing?

## Notes

Add anything maintainers should know.
