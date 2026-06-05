# TUC Governance

TUC is being structured as a serious open-source project from Phase 1 onward.
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
- Enforcing secure-by-design review gates.

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

## License

TUC is licensed under Apache-2.0. Contributions intentionally submitted to the
project are accepted under the same license unless a separate written agreement
states otherwise.
