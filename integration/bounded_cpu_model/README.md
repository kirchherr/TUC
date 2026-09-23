# Installed reusable CPU model consumer

This standalone standard-library client imports no TUC code. It owns six graphs:
Linear, calibrated classifier and scaled attention, each in two shape profiles.
It packs graphs with fixed parameters through the installed CLI, independently
checks the canonical model and its FP32 bit identity, compares inspection with
the ordinary graph program, and executes changing inputs and batches.

Copy this directory outside the checkout beside an installed wheel environment
on supported Linux x86-64 with local Docker:

```sh
python3 -I consumer.py
python3 -I consumer.py --run
```

Default mode prints an inert candidate. Explicit execution requires seven model
packs, thirteen single runs and six two-request batches. One Linear variant
changes fixed weights and requires a different model identity with an unchanged
program identity. Another batch shares all variable inputs between requests.

The fixed corpus checks 110 output scalars: 38 bitwise FP32 Linear outputs and
72 composed outputs with absolute tolerance `2e-6` plus relative tolerance
`2e-5`. Twelve visible classifier probability rows must be positive, at most
one, and sum within `8e-6` of one. NumPy tests evaluate separate graph equations.

Eight malformed-data controls cover duplicate keys, external references, bad
parameter lengths, subnormals, no remaining input, single/batch overrides and
a malformed last request. Two numeric controls use valid normal inputs to cause
overflow in a single run and the last request of a batch. Exact closed errors,
empty stdout, unchanged fixtures and clean workspaces are required.

Only complete success creates `record.json`. It binds original graph, parameter,
canonical model and input bytes with program/model/request/batch identities,
expected and observed outputs, and control identities. Digests do not
authenticate evidence. Inert candidates and synthetic tests are not native
observations. Actual installed execution is pending CI.
