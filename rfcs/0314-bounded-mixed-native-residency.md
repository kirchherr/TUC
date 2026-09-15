# RFC 0314: Shared Residency Planning and Bounded Mixed Native Execution

Status: Implementing; native evidence pending

## Scope

Add an opt-in, data-only post-partition residency planner in `tuc.runtime.residency`.
It combines external inputs, inter-operation transfers, compute assignments and
terminal publication into one ordered schedule. Named logical address spaces
remain distinct even when their physical memory kinds match or are unknown.
Existing partition dumps, prototype cost estimates and runtime admission do not
change. Copies are counted by actual planned bytes, not inferred latency.

The closed native experiment compares all-C11 with GPU Matmul -> CPU ReLU -> GPU
axis-1 Sum for the existing A[33,7], B[7,5] corpus. This forces both intermediate
copy directions and uses unchanged generated C11/CUDA arithmetic and reference
semantics. Capabilities select one eligible backend per operation family; this
does not prove optimal placement, asynchronous scheduling or native performance.

## Planner Invariants

The typed graph and partition must agree in name, operation order, placement,
physical domains and row-major layout. Inter-operation physical-domain transfers
must match exactly. All inputs start in an explicit host space, and every terminal
output is published there. Values are immutable and single-producer; forward
references, in-place writes, layout conversion and aliasing are rejected. Resident
copies may serve multiple consumers; buffers are not reused. No allocations or
device discovery occur in the planner. Input bounds: 64 operations, 256 tensor
ports, 16 backend mappings, 512 slots, 128 MiB aggregate logical storage. Names
are bounded identifiers. No serialized native plans or executable metadata enter.

## Native Exception and Security

Only a freshly reconstructed fixed plan lowers to a compiled table. A closed
worker independently validates slot bounds, sizes, tensor identities, spaces,
write-once availability, operation order and required native target placement
before GPU discovery or allocation. Each run starts with no available values;
copies become available only after successful synchronized transfer. Missing
transfer or output publication must fail, not use an earlier run's buffer.

The operator inherits RFC 0313's pinned toolchains, deny-default context, no
network/host mounts, non-root read-only worker, capability drop, seccomp,
no-new-privileges and bounded CPU/RAM/PIDs/time. C11 sanitizers remain required;
the mixed binary links a fixed C11 object and SASS-only sm86 kernels, without
PTX/JIT or external plugins. GPU driver faults remain a host risk; container
limits do not fully isolate the GPU or cap VRAM. Recheck an idle reviewed host
before execution and leave unrelated services untouched.

## Acceptance

Both actual targets must pass ten cases plus replay and 363 scalar checks against
the unchanged ordered FP32 and rational-interval oracle. Mixed execution must
report 11 CPU and 22 GPU calls, 33 uploads (18964 bytes) and 22 downloads (8712
bytes), with per-run residency completion. Validate compiled malformed-schedule,
missing-copy/publication and wrong-code controls. Accept new bound observations
only after recording the source commit and transferred archive digest. Keep old
records unchanged. CI executes the CPU path and revalidates recorded GPU metadata.
Same-maintainer evidence is not independent reproduction or hardware attestation.

Normal-runtime native admission, arbitrary source/shapes/inputs, multi-device
execution, layout conversion, performance and independent reproduction stay open.
