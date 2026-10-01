# Compile a bounded model into capability-planned artifacts

RFC 0336 connects the existing fixed-parameter model format to TUC's bounded,
capability-driven artifact compiler:

```python
from tuc.compiler.bounded_model_artifacts import compile_bounded_model_artifacts

compiled = compile_bounded_model_artifacts(model_bytes, backend_bindings)
print(compiled.model_digest)
print(compiled.model_compilation_digest)
print(compiled.parameter_bindings)
print(compiled.variable_input_bindings)
print(compiled.source_compilation.compilation.dump_decision_report())
files = compiled.source_compilation.artifacts.files()
```

The caller supplies the same explicit `BoundedBackendBinding` records used by
the public bounded Source Intent compiler. TUC validates the complete model,
plans every operation without fallback, and emits inert C11/CUDA source text.
Fixed parameters remain FP32 data bound to exact artifact tensor positions;
they are not embedded into code or uploaded to a device. Remaining inputs stay
explicit for a later application boundary.

The model-compilation digest binds the model, capability set, Source Intent,
public I/O, fixed parameter bits and every generated artifact file. Use
`validate_bounded_model_artifacts` before consuming a result after it crosses a
trust boundary.

This API performs no filesystem access, native compilation, runtime execution,
plugin discovery, device access, network call or subprocess. The generated
source has no execution authorization. See [RFC 0336](../rfcs/0336-bounded-model-artifacts.md).
