# Objective Delta Audit Inputs

This directory contains the public fixed-value conformance vector and the
standalone standard-library reproducer for Objective Delta.

The reproducer reads the existing Source Intent and two backend packages from
`integration/objective_delta`, rebuilds the two-operation placement and layout
conversion, evaluates the fixed `2 x 2` semantics, and emits a digest-only
report. It does not import TUC or NumPy.

The vector deliberately publishes the small non-sensitive input and expected
output values so reviewers can implement the contract themselves. These raw
values do not enter Objective Delta's metadata-only proof report or release
receipt.
