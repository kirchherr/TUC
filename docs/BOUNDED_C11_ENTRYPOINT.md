# Emit a checked C11 function for a bounded graph

The public `tuc.compiler.bounded_c11` API emits one callable C11 function for a
complete CPU graph. It owns intermediate storage and scheduling, so a C caller
provides only input and output buffer descriptors. The Python API returns source
text and metadata; compilation and execution are separate actions.

First construct a module and backend bindings as described in the
[bounded Source Intent guide](BOUNDED_SOURCE_COMPILER.md), then:

```python
from tuc.compiler import compile_bounded_source_intent
from tuc.compiler.bounded_c11 import (
    emit_bounded_c11_entrypoint,
    validate_bounded_c11_entrypoint,
)

compiled = compile_bounded_source_intent(module, bindings)
entrypoint = emit_bounded_c11_entrypoint(module, bindings, compiled)
validate_bounded_c11_entrypoint(module, bindings, compiled, entrypoint)
print(entrypoint.entrypoint_symbol)
files = entrypoint.files()  # entrypoint.h, entrypoint.c, entrypoint.json
```

The emitter accepts selected C11 operations and host storage with no transfers.
Mixed or CUDA plans reject. Existing graph, storage and arithmetic bounds remain
in force. Revalidation covers the original compilation and all new source text.

The generated function takes four arguments: a `const struct tuc_c11_input *`,
its descriptor count, a `const struct tuc_c11_output *`, and its count. Each
descriptor contains a float pointer and an exact `size_t elements` count.
Order matches `compiled.input_bindings` and `compiled.output_bindings`.
The digest-derived function name is available as `entrypoint_symbol` and in
the manifest. Distinct graphs can be linked together; their common ABI types
are compatible and their exported symbols differ.

| Status | Meaning |
| --- | --- |
| `TUC_C11_OK` | Every output has been copied to the caller's buffers. |
| `TUC_C11_ARGUMENT` | Descriptor, extent, alignment or overlap is invalid. |
| `TUC_C11_NUMERIC` | An input or arithmetic intermediate violates the numeric contract. |
| `TUC_C11_ENVIRONMENT` | The floating-point environment is unsupported. |

All buffers must be disjoint, including inputs. All tensor storage must also avoid
both descriptor arrays, which must be disjoint from each other. The function checks ranges and copies inputs into fixed
owned storage. On a returned error, every caller output remains unchanged.
Callers must still provide valid live storage and avoid concurrent mutation;
the ABI cannot validate whether arbitrary native pointers are accessible.

The reviewed target is Linux x86-64/SSE2. Build as C11 with contraction and
fast-math disabled and `-frounding-math` enabled. Round-to-nearest, disabled FTZ/DAZ and masked SSE exceptions
are checked before arithmetic. Every product and addition is checked after
binary32 rounding. Non-finite/subnormal results and nonzero products rounded to
zero reject. Zero operands and exact cancellation remain valid. No tolerance
or performance guarantee is implied.

The [installed client](../integration/bounded_c11_entrypoint/README.md) links two
graphs and checks actual static/sanitized execution against independent FP32
references. Its [workflow](../.github/workflows/bounded-c11-entrypoint.yml)
installs the wheel outside the checkout and records source-bound observations.
See [RFC 0323](../rfcs/0323-bounded-c11-graph-entrypoint.md) for the exact boundary.

Earlier C11 and GPU observations keep their original scope. General native
runtime admission, CUDA execution of this entrypoint and arbitrary-input
correctness remain outside this slice.
