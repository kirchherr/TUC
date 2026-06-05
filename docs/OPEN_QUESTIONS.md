# Open Questions

## License

TUC needs a final open-source license before public release or broad contributor
onboarding.

Candidate directions:

- Apache-2.0 for broad commercial compatibility and patent language.
- Apache-2.0 WITH LLVM-exception if the project needs closer alignment with
  LLVM ecosystem norms.
- MIT if the project wants a very permissive minimal license.

This is a project-owner decision.

## Triton Integration Strategy

Possible paths:

- Fork Triton and implement TUC inside the fork.
- Build TUC as a prototype layer first, then integrate with Triton once the
  contracts are proven.
- Build a backend or extension path that avoids maintaining a long-lived fork.

Recommended Phase 0 approach: prototype first, fork only when the integration
surface is understood.

## First Hardware Class

Photonics is the strongest first exotic target because the split between linear
analog operations and digital nonlinear operations is easy to explain and test
with a simulator.
