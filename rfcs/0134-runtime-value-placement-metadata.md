# RFC 0134: Runtime Value Placement Metadata

## Status

Accepted.

## Context

Runtime Tensor Store v0 records accepted runtime values as immutable
`RuntimeValueRecord` objects. Runtime planning already knows planned backend,
memory domain, and produced layout for computed values, but that information was
visible mainly in plan, compiler-decision, and trace artifacts.

For heterogeneous runtime proofs, value records need to expose planned placement
metadata so review evidence can connect runtime values back to placement
decisions.

## Decision

Extend `RuntimeValueRecord` with:

- `planned_backend`
- `planned_memory_domain`
- `planned_layout`
- `placement_source`

External inputs use:

```text
planned_backend = external_input
planned_memory_domain = host_ram
planned_layout = row_major
placement_source = external_input_boundary
```

Computed records use:

```text
placement_source = partition_plan
```

and copy planned backend, memory domain, and layout from the accepted runtime
assignment.

Runtime Tensor Store Evidence now compares observed record placement metadata
against expected placement metadata derived from the same `PartitionPlan`.

Schema coverage remains in:

```text
schemas/runtime_tensor_store_evidence_report.v0.schema.json
```

## Security Boundary

Placement metadata is logical planning metadata only. It is not a device handle,
allocation handle, physical address, stream ID, runtime handle, proof of device
residency, plugin entrypoint, backend artifact, generated code, benchmark
sample, or execution authorization.

The existing Runtime Executor blocked surfaces remain blocked: no plugin
discovery, device access, dynamic imports, dynamic libraries, generated
artifact execution, JIT execution, network access, or subprocess execution.

## Consequences

The Systolic proof path can now connect planned `device_sram` and `blocked`
layout semantics to runtime value records through metadata-only evidence.

Future allocator work still requires Runtime Allocation Plan, Runtime Memory
Budget, Runtime Allocation Request Manifest, and a separate allocator RFC before
any real allocation behavior is accepted.
