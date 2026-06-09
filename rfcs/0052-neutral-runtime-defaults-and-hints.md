# RFC 0052: Neutral Runtime Defaults And Hints

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Alpha / Epsilon alignment

## Summary

TUC removes GPU as the implicit runtime fallback and removes the hardware-class
hint name `prefer_analog_linear`.

The default fallback backend is now `reference-cpu` in `host_ram`. GPU remains a
valid backend only when represented by explicit backend capability data.

Developer-facing hints now use `prefer_linear_accelerator`, which expresses
compute intent without naming analog hardware. Backend capability and runtime
planning layers remain responsible for deciding whether a linear operation maps
to analog, photonic, digital, systolic, in-memory, CPU-vectorized, GPU, or any
future backend class.

## Motivation

TUC is The Universal Compute, not a GPU-centered compiler. Keeping `gpu` as the
implicit fallback made the early prototype easy to explain, but it gave one
hardware family an architectural privilege. Likewise, `prefer_analog_linear`
named a hardware class in frontend-facing metadata.

Both details work against HAC-IR neutrality and long-term hardware
independence.

## Decision

Add:

- `DEFAULT_FALLBACK_BACKEND = "reference-cpu"`
- `DEFAULT_FALLBACK_MEMORY_DOMAIN = MemoryDomainKind.HOST_RAM`

Use those defaults in `partition_graph`, `CompilerPipeline`, and
`compile_graph`.

Rename:

- `prefer_analog_linear` -> `prefer_linear_accelerator`

The Triton metadata adapter rejects `prefer_analog_linear` as an unsupported
hint rather than silently aliasing it. This is intentional: hardware-class names
must not survive as accepted frontend metadata.

## Consequences

- Unsupported operations fall back to `reference-cpu`, not `gpu`.
- Movement defaults prefer `host_ram`, not `gpu_hbm`.
- Runtime-plan and compiler-decision goldens now show CPU reference fallback
  unless a GPU backend is explicitly registered.
- GPU examples remain valid when expressed through `BackendCapability`.
- The linear simulator can still use `analog_weight_bank` internally as
  capability evidence; this does not make "analog" a frontend hint.

## Rejected Alternatives

1. Keep `gpu` as the default until a real CPU backend exists.

   Rejected because the default name is already architectural evidence in
   goldens, docs, and proof reports.

2. Keep `prefer_analog_linear` as a backward-compatible alias.

   Rejected because silent aliases keep hardware-class language alive in the
   frontend contract.

3. Rename the simulator memory domain in the same change.

   Rejected for scope control. Memory-domain taxonomy and simulator naming need
   a separate capability-model cleanup.
