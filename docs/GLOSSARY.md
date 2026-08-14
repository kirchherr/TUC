# TUC Glossary

This glossary explains the compiler and TUC-specific terms used in the public
research claim. Definitions describe the current prototype, not a future
product.

## General Terms

### Compiler

A program that translates one representation of a computation into another.
Traditional compilers often translate source code into machine code. TUC
currently translates bounded descriptions of computation into inspectable
plans and executes only fixed research slices through built-in prototype
executors.

Further reading:
[LLVM compiler tutorial](https://llvm.org/docs/tutorial/MyFirstLanguageFrontend/index.html).

### Tensor

A typed multidimensional array. A scalar has rank zero, a vector rank one, and
a matrix rank two. Objective Delta uses four `2 x 2` `float64` tensors.

### Operation

One step in a computation, such as matrix multiplication or applying a function
to every array element.

### Compute Intent

A description of what calculation should happen, including operations, tensor
shapes, data types, outputs, and constraints, without selecting a physical
device. This is the project idea; it is not an established industry term with
one universal definition.

### Intermediate Representation (IR)

A structured form used between an input language and a target implementation.
IRs make program meaning and compiler decisions easier to analyze and transform
than raw source text or machine code.

Further reading: [MLIR overview](https://mlir.llvm.org/).

### Frontend

The part of a compiler that accepts an input language or data format and turns
it into an internal representation. TUC does not yet accept arbitrary Python or
Triton programs as production input.

### Backend

The part that maps a plan to a target implementation. TUC keeps two concepts
separate:

- a **backend capability description** is bounded JSON data stating what a
  target claims to support; and
- a **backend executor** is code that performs operations.

Objective Delta reads two external capability descriptions but executes only
TUC's built-in NumPy-based simulators. It does not execute code supplied by the
external descriptions.

### Capability

A declared property of a target, such as supported operations, accepted memory
layouts, or output layouts. A declaration is input to planning, not proof that
real hardware exists or performs as claimed.

### Planner And Placement

The planner selects which eligible backend should handle each operation.
Placement is the resulting assignment. In Objective Delta, matrix
multiplication is assigned to the systolic simulator and the elementwise step
to the vector simulator.

### Memory Layout

The order or grouping used to represent tensor elements in memory. Different
targets may require different layouts. Objective Delta records a planned
`blocked -> row_major` conversion between its two simulated placements; it does
not claim that physical device memory was converted.

### Runtime

The code that carries out an already validated plan. TUC's current runtime is a
Python research runtime with a fixed registry of trusted in-process executors.

### Reference Semantics

A deliberately simple implementation used as the expected meaning of an
operation. TUC compares candidate execution with a separate CPU reference to
detect semantic drift.

### Backend Equivalence

A check that two allowed execution placements produce the same observable
result within the stated tolerance. It does not mean the placements have equal
performance, energy use, or physical behavior.

### Simulator Or Prototype Backend

Software that models a target role without executing on that physical target.
TUC's `systolic-sim` and `vector-sim` currently execute NumPy operations on the
host CPU.

### Native Execution

Execution through code generated for, or a library controlling, an actual
target such as a GPU, NPU, or accelerator. Objective Delta does not include
native execution.

## TUC-Specific Terms

### Source Intent

TUC's schema-versioned plain-data input describing tensors, operations, return
values, and bounded hints. See [Source Intent IR](SOURCE_INTENT_IR.md).

### HAC-IR

TUC's Hardware-Agnostic Compute intermediate representation. It is intended to
retain operation meaning and constraints without embedding vendor or device
selection. See [HAC-IR Semantic Charter](HAC_IR_SEMANTIC_CHARTER.md).

### HS-IR

TUC's Hardware-Specific intermediate representation, where reviewed target
choices may be attached after neutral intent has been preserved. See
[HS-IR Dialect](HS_IR_DIALECT.md).

### Evidence

Structured metadata that records what was accepted, planned, executed, or
compared. Public TUC evidence omits raw tensor values by policy. Evidence makes
a narrow result reviewable; it does not turn a simulator result into a hardware
or performance result.

### Evidence Gate

A deterministic PASS/FAIL check over a fixed evidence contract. A gate checks
declared invariants and blocked claims. It is a project verification mechanism,
not a formal proof of all compiler behavior.

### Reproduction Receipt

The deterministic metadata-only JSON emitted after replaying Objective Delta.
It binds artifact digests and observed checks without serializing tensors or
claiming that the maintainer's execution is independent.

### Artifact Attestation

A signed provenance statement connecting a release artifact to the workflow
that produced it. An attestation helps verify origin and build identity; it does
not prove that the software is safe.

Further reading:
[GitHub artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations).

### Reproducible Result

A result another party can obtain from the stated inputs and procedure. TUC's
current request asks for independent reproduction of one semantic experiment,
not byte-identical rebuilding of every distribution artifact.

Further reading: [Reproducible Builds definition](https://reproducible-builds.org/docs/definition/).
