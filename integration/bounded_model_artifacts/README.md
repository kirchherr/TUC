# Bounded model artifacts installed consumer

`consumer.py` uses only public TUC APIs to compile one fixed-parameter model
under CPU-only, CUDA-only and mixed capability sets. It verifies a second model
with changed parameter bits produces identical graph source artifacts but a new
model and model-compilation identity.

The report contains digests, binding names and planner backend sequences. It
contains no model values, generated source, paths, runtime handles or device
identifiers. The consumer does not compile or execute generated code.

Run from an environment containing an installed TUC wheel:

```text
python -I consumer.py
```
