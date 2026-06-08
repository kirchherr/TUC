# Softmax Operation-Family Planning

Softmax is part of TUC's MVP operation family, but it is not treated as a
simple elementwise operation.

This document defines the planning contract that must hold before TUC adds
softmax proof graphs, softmax HAC-IR goldens, softmax runtime-plan goldens, or
softmax compiler decision-report goldens.

## Why Softmax Needs Its Own Contract

Softmax combines nonlinear exponentiation, reduction, normalization, and
numerical-stability requirements. It is common in transformer workloads and is a
useful boundary for proving that TUC can preserve compute intent while runtime
planning decides where pieces should execute.

The important claim is:

```text
HAC-IR preserves softmax intent.
Runtime planning may later explain placement or decomposition.
No backend is allowed to redefine softmax semantics.
```

## Compute Intent

In HAC-IR, `softmax` means a numerically stable softmax over a validated tensor
axis.

The reference semantics are:

```text
shifted = input - max(input, axis, keepdims=True)
exp = exp(shifted)
output = exp / sum(exp, axis, keepdims=True)
```

The current in-repository reference kernel is `reference_softmax(...)`.

Future proof graphs must make the axis explicit and validate that:

- the axis is an integer
- the axis is in bounds for the input rank
- the input and output shapes match exactly
- input values are finite before reference execution
- output dtype and shape preserve the operation contract

Negative axes may be accepted only after canonicalization to an in-bounds axis.

## HAC-IR Boundary

HAC-IR may express:

- operation family: `softmax`
- tensor names, shapes, dtypes, inputs, and outputs
- operation linearity as `nonlinear`
- validated user intent such as `max_error_budget`
- compiler-produced movement estimates
- compiler-produced preferred memory-domain planning constraints

HAC-IR must not express:

- backend assignment
- decomposition into backend-specific kernels
- vendor names
- device names
- generated artifacts
- approximation algorithms
- lookup-table details
- calibration artifacts
- measured performance
- backend-specific noise modules

Softmax axis is compute intent. The current prototype may carry it as a
non-namespaced operation attribute, but future namespaced `tuc.*` axis attribute requires an explicit dialect RFC and negative tests.

## Runtime Planning Boundary

Runtime planning may later choose among:

- keeping softmax as one operation assigned to a backend that explicitly
  supports it
- assigning softmax to the fallback backend when no registered capability
  accepts it
- decomposing softmax into reduction and elementwise stages

Decomposition is not a HAC-IR semantic rewrite. It is a runtime/HS-IR planning
decision that must remain visible through:

- compiler decision reports
- runtime-plan dumps
- candidate score diagnostics
- transfer edges
- layout conversions
- proof reports and golden fixtures

If decomposition changes numerical behavior, error bounds, transfer movement,
or fallback semantics, the proof must fail closed until the behavior is
documented and golden-tested.

## Capability Boundary

Backend capability data may claim support for `softmax` as pure data.

Capability checks must not:

- execute backend code
- discover plugins
- import modules
- spawn subprocesses
- load dynamic libraries
- access devices
- execute generated artifacts
- touch the network
- read host paths
- read environment variables

A backend that supports only matmul, reduction, or elementwise pieces must not be treated as supporting whole-operation softmax unless decomposition is explicitly planned and reported.

## Movement And Scoring

The current movement estimator treats softmax as exact input/output shape with
approximate arithmetic count. That estimate is planning evidence, not a
numerical proof and not a performance claim.

Future candidate scoring may add softmax-specific components only when they are:

- bounded
- deterministic
- derived from validated graph and capability data
- documented outside HAC-IR semantics
- visible in candidate score diagnostics
- covered by runtime-plan and compiler decision-report goldens

Noise/error-budget assumptions for specialized hardware must stay in backend
capability data, runtime plans, proof reports, or future calibration artifacts,
not in HAC-IR softmax semantics.

## Proof Gate

Before a softmax proof graph is accepted, the PR must include:

- deterministic independent `reference_softmax(...)` validation
- HAC-IR golden dump
- runtime-plan golden dump
- compiler decision-report golden dump
- proof report ending in `PASS`
- explicit axis validation in the proof graph or frontend adapter
- review of fallback behavior and transfer movement
- confirmation that no plugin, subprocess, dynamic-library, device, network,
  generated-artifact, host-path, or environment-dependent surface was added

Softmax proof artifacts are compiler-contract changes and must be reviewed as
hardware-independence evidence, not just numerical fixtures.
