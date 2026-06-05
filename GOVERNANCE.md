# TUC Governance

TUC is being structured as a serious open-source project from Phase 0 onward.
This governance model is intentionally lightweight until the project has a
larger contributor base.

## Roles

### Maintainers

Maintainers are responsible for:

- Reviewing pull requests.
- Accepting or rejecting RFCs.
- Protecting compatibility and project scope.
- Maintaining CI, tests, documentation, and release quality.
- Coordinating backend and runtime design decisions.

### Contributors

Contributors may propose code, tests, documentation, examples, and RFCs.

### Backend Authors

Backend authors maintain hardware-specific or simulator-specific integrations.
Backends should declare capabilities, constraints, costs, and validation tests.

## Decision Process

Small changes may be merged through ordinary pull request review.

Architectural changes require an RFC. An RFC is accepted when maintainers agree
that it is:

- Aligned with the roadmap.
- Testable.
- Narrow enough to implement.
- Compatible with the current MVP scope or explicitly expands it.

## Compatibility

Phase 0 has no stable public API. Compatibility promises begin only after an API
or RFC is explicitly marked as stable.

## License Decision

The final open-source license is not yet selected. This must be resolved before
public release, wide contributor onboarding, or accepting significant external
contributions.
