# Compile Source Intent into bounded DAG artifacts

The public `tuc.compiler.bounded_source` API joins validated Source Intent,
capability-based placement and the reusable C11/CUDA artifact compiler. An
installed application can provide its own bounded graph without importing the
repository's examples or choosing a predefined graph family.

RFC 0328 adds [CPU Linear](BOUNDED_CPU_LINEAR.md) using the existing Matmul family
with `rhs_transposed: true`. Graphs containing this form use the distinct
`tuc.bounded_linear_dag_artifacts.v0` manifest and require one C11 CPU backend;
ordinary and transposed Matmul, Add/Bias, ReLU and Sum can be composed within
the existing bounded graph limits.

```python
from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_source import (
    BoundedBackendBinding,
    compile_bounded_source_intent,
    validate_bounded_source_compilation,
)
from tuc.frontend.source_intent import (
    SourceIntentModule, SourceIntentOperation, SourceIntentReturn, SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.ir.modules import IRStage

module = SourceIntentModule(
    name="application_projection",
    tensors=tuple(SourceIntentTensor(name, (2, 2)) for name in ("a", "b", "p", "y")),
    operations=(
        SourceIntentOperation("project", "matmul", ("a", "b"), ("p",)),
        SourceIntentOperation(
            "activate", "elementwise", ("p",), ("y",),
            attributes={"elementwise_kind": "relu"},
        ),
    ),
    returns=(SourceIntentReturn("result", "y"),),
)
bindings = (
    BoundedBackendBinding(
        BackendCapability(
            name="host",
            supported_ops=frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE}),
            memory_domain=MemoryDomainKind.HOST_RAM,
        ),
        DAGTarget.C11,
    ),
)
result = compile_bounded_source_intent(module, bindings)
validate_bounded_source_compilation(module, bindings, result)
print(result.compilation.dump(IRStage.HAC_IR))
print(result.compilation.dump_decision_report())
print(result.output_bindings)
files = result.artifacts.files()  # New dictionary of source text; no file writes.
```

The result contains the existing `CompilationResult`, immutable artifact texts,
typed public I/O bindings and canonical source/capability digests. An I/O
binding provides the public name, tensor identity, manifest index, shape and
dtype. All terminal outputs must be explicitly returned with `required=True`.
Public aliases and their order are preserved.

Use one or two exact `BoundedBackendBinding` records in a tuple. C11 capabilities
use `MemoryDomainKind.HOST_RAM`; CUDA sm86 capabilities use
`MemoryDomainKind.UNKNOWN`, matching the compiler's abstract accelerator space.
Both use row-major layouts. Declare supported/preferred operation kinds to
change planning. TUC then selects assignments and records its reasons,
candidates and transfers. A missing capability produces a rejection rather
than an implicit fallback. Backend name order is canonicalized; an unused
capability still contributes to the binding digest.

The accepted language is deliberately small: static row-major FP32, ranks one
and two, dimensions 1–64, Matmul, explicit ReLU and `axis=1` Sum. The facade
checks at most eight operations, 24 tensors and one million scalar arithmetic
steps before adapting or planning. It rejects unsupported semantics, malformed
types, incorrect shapes/SSA, unused declarations, incomplete/optional returns,
invalid capabilities and metadata above the existing bounded contract.
Post-planning limits remain 48 buffers, 96 events, 256 KiB planned storage,
64 KiB metadata and 256 KiB artifact text.

RFC 0327 extends the C11 CPU path with equal-shape tensor Add and right-hand
row bias `[M,N] + [N]`. Add-containing graphs use the separate
`tuc.bounded_add_dag_artifacts.v0` manifest, require one selected C11 CPU
backend, and reject CUDA or mixed placement.
See the [Add/Bias guide](BOUNDED_CPU_ADD_BIAS.md) for an affine/MLP example.

`validate_bounded_source_compilation` replays this pure compilation from the
original module and bindings and checks every result field. Call it again after
passing results across code boundaries: the existing compilation's metadata
dictionaries remain mutable. A changed artifact, decision, I/O binding, source
or capability is rejected. This is consistency verification, not cryptographic
attestation or proof that any generated code ran.

The mapping-proxy check conservatively requires an ordinary dictionary backing
store, inspected without dispatching mapping hooks. It is tested on CPython;
an unsupported interpreter representation fails closed. The API is not a
sandbox for Python callers or concurrent mutation of their objects.

See the [standalone installed consumer](../integration/bounded_dag_compiler/README.md)
for a branching graph with three Matmuls, four inputs and two public outputs.
It demonstrates automatic CPU/GPU/mixed placement with unchanged HAC-IR and
arithmetic. Its tests replay manifest data with independent Python binary32
arithmetic. The [installed-consumer CI](../.github/workflows/bounded-source-consumer.yml)
checks an actual wheel from outside the source checkout.

No call compiles native source, loads a library, discovers plugins, contacts a
device or executes generated code. The [earlier physical matrix](BOUNDED_DAG_NATIVE_EVIDENCE.md)
continues to cover only its original fixed graphs and source binding. General
native runtime admission, arbitrary-input numerical correctness and performance
claims remain unavailable. See [RFC 0321](../rfcs/0321-bounded-source-intent-compiler.md).
