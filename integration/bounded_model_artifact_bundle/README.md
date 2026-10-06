# Bounded model artifact bundle consumer

This installed-style consumer creates and validates CPU, CUDA and mixed
capability bundles through the public API. Its deterministic report contains
only identities, sizes and security-boundary facts; generated source and fixed
parameter values are excluded.

Run it from the repository environment with:

```text
python -m integration.bounded_model_artifact_bundle.consumer
```

The output must match the closed schema and committed golden report.
