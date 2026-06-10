# Backend Capability Schema

Backend capability data is TUC's hardware self-description layer. It lets a
backend say what it can accept without putting backend-specific implementation
details into HAC-IR.

The current schema is:

```text
tuc.backend_capability.v0
```

Transfer-cost profiles use a related but separate schema:

```text
tuc.transfer_cost_profile.v0
```

Both schemas are declarative data only. Loading them must not discover plugins,
import modules, spawn subprocesses, load dynamic libraries, touch devices, open
network connections, or execute generated artifacts.

## Capability Manifest Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `schema_version` | yes | Must be `tuc.backend_capability.v0`. |
| `name` | yes | Stable backend name used in diagnostics and HS-IR assignments. |
| `supported_ops` | yes | Operation families the backend can accept. |
| `supports_noise_model` | no | Whether the backend can model numeric or physical noise. |
| `supports_calibration` | no | Whether the backend has a documented calibration path. |
| `preferred_for` | no | Supported operation families the planner may prefer for this backend. |
| `max_error_budget` | no | Maximum operation error budget accepted by capability checks. |
| `memory_domain` | no | Memory domain where backend outputs reside after execution. |
| `supported_layouts` | no | Tensor layouts accepted as inputs. |
| `produced_layouts` | no | Tensor layouts the backend may emit. |

Valid operation families are:

- `matmul`
- `elementwise`
- `reduction`
- `softmax`

Valid memory domains and layouts are defined by `MemoryDomainKind` and
`LayoutKind` in `tuc.ir.memory`.

## Error-Budget Assumptions

`max_error_budget` is an acceptance limit, not a correctness proof.

When present, it means:

- The value must be finite and non-negative.
- Operations with no requested `max_error_budget` are accepted unless another
  capability field rejects them.
- Operations with a requested budget above the backend limit are rejected by
  pure-data capability checks.
- The field describes backend tolerance, not measured error, benchmark quality,
  or hardware certification.

Requested operation error budgets belong to compute intent and planning
constraints. Backend-specific measurement, calibration data, or correction
algorithms do not belong in HAC-IR and must not be hidden inside the capability
manifest.

## Latency And Energy Assumptions

Backend capability manifests do not contain latency or energy fields.

Transfer latency and energy assumptions live in
`tuc.transfer_cost_profile.v0` manifests because they describe movement between
memory domains rather than whether a backend accepts an operation.

Transfer-cost profile fields are:

| Field | Meaning |
| --- | --- |
| `schema_version` | Must be `tuc.transfer_cost_profile.v0`. |
| `name` | Stable profile name. |
| `fallback` | Default transfer parameters for unspecified domain pairs. |
| `edges` | Optional domain-pair overrides. |
| `bandwidth_gb_s` | Positive finite decimal GB/s. In the prototype, 1 GB/s equals 1 byte/ns. |
| `base_latency_ns` | Finite non-negative fixed transfer latency. |
| `energy_pj_per_byte` | Finite non-negative transfer energy per byte. |
| `source_domain` | Source memory domain for an override edge. |
| `target_domain` | Target memory domain for an override edge. |

These values are deterministic planning assumptions. They are not proof of real
hardware performance, real energy use, or vendor claims. Runtime plans must
remain inspectable when these assumptions affect placement decisions.

## Calibration Assumptions

`supports_calibration` is a capability flag only.

When `true`, it means the backend author claims the backend can participate in
a future calibration workflow. It does not mean calibration was performed, that
calibration data is bundled, or that TUC may read device state.

Calibration data, benchmark output, hardware serial numbers, device paths,
vendor tools, and runtime handles are not valid capability-manifest fields. Any
future calibration-artifact format needs its own schema, threat model, resource
budgets, and sandboxing rules.

## Noise-Model Assumptions

`supports_noise_model` means a backend can describe or simulate noise effects
within a future backend-specific contract. It does not grant permission to
change HAC-IR semantics or silently accept operations outside declared error
budgets.

Noise-model details are backend-specific. They should be documented in backend
author material and checked by conformance extensions, not encoded as ad hoc
HAC-IR attributes.

## Validation And Security

Manifest loading is schema-versioned and bounded:

- JSON files must use the `.json` suffix.
- Symlinks are rejected.
- Files must be UTF-8 and within the manifest byte budget.
- Duplicate JSON keys are rejected.
- Unknown fields are rejected.
- Numeric values must be finite and bounded.
- Manifest nesting, object key count, list length, string size, and numeric
  range are limited.

Capability checks are pure data checks. They may inspect operation kind, layout,
and error-budget attributes, but they must not call backend lowering, import
backend code, access devices, or execute artifacts.

## Invalid Or Misleading Examples

These examples must be rejected or moved to another contract.

Some invalid examples are rejected directly by the bounded manifest loader.
Other syntactically valid but overreaching examples are blocked by
[Manifest Claim Review](MANIFEST_CLAIM_REVIEW.md), whose schema is
`schemas/manifest_claim_review_report.v0.schema.json`.

### Latency Or Energy In A Backend Manifest

Invalid:

```json
{
  "schema_version": "tuc.backend_capability.v0",
  "name": "too-much-in-one-manifest",
  "supported_ops": ["matmul"],
  "bandwidth_gb_s": 128.0,
  "base_latency_ns": 2500.0,
  "energy_pj_per_byte": 12.0
}
```

Why this is wrong: latency and energy assumptions belong to
`tuc.transfer_cost_profile.v0`, not backend operation-acceptance data.

### Calibration Evidence In A Capability Manifest

Invalid:

```json
{
  "schema_version": "tuc.backend_capability.v0",
  "name": "calibrated-by-claim",
  "supported_ops": ["matmul"],
  "supports_calibration": true,
  "calibration_data": "device-run-2026-06-08.json",
  "hardware_serial": "vendor-device-0"
}
```

Why this is wrong: `supports_calibration` is a capability flag, not calibration
evidence. Calibration artifacts need a separate schema and security review
before TUC may accept them.

### Performance Or Certification Claims

Invalid:

```json
{
  "schema_version": "tuc.backend_capability.v0",
  "name": "marketing-claim",
  "supported_ops": ["matmul"],
  "benchmark_score": "fastest",
  "hardware_certificate": "certified"
}
```

Why this is wrong: benchmarks, certifications, and measured artifacts are not
capability fields. They need provenance and review rules before they can inform
TUC decisions.

### Impossible Or Misleading Error Budgets

Invalid:

```json
{
  "schema_version": "tuc.backend_capability.v0",
  "name": "bad-error-budget",
  "supported_ops": ["matmul"],
  "max_error_budget": -0.1
}
```

Why this is wrong: error-budget limits must be finite and non-negative. A
backend must not use an invalid limit to imply correctness or certification.

### Overbroad Specialized Accelerator Claims

Blocked by Manifest Claim Review:

```json
{
  "schema_version": "tuc.backend_capability.v0",
  "name": "invalid-universal-accelerator",
  "supported_ops": ["matmul", "elementwise", "reduction", "softmax"],
  "preferred_for": ["matmul", "elementwise", "reduction", "softmax"],
  "memory_domain": "device_sram",
  "produced_layouts": ["blocked"]
}
```

Why this is wrong: a non-reference backend claiming every MVP operation family
is a strategic claim, not a simple capability fact. It needs a dedicated RFC,
conformance evidence, runtime executor evidence, and maintainer review before
it can be accepted.

### Noise Without Error-Budget Boundary

Blocked by Manifest Claim Review:

```json
{
  "schema_version": "tuc.backend_capability.v0",
  "name": "invalid-noise-without-budget",
  "supported_ops": ["matmul"],
  "supports_noise_model": true
}
```

Why this is wrong: a noise-model claim implies approximate or variable
behavior. TUC requires an explicit `max_error_budget` boundary before such a
claim can pass review.

## Reviewer Checklist

Before accepting a capability-schema change, verify:

- The field describes backend capability data, not backend executable behavior.
- The field belongs in capability data rather than HAC-IR, HS-IR, runtime
  plans, transfer-cost profiles, or backend lowering.
- The field has bounded validation and fail-closed rejection tests.
- The field does not introduce plugin discovery, imports, subprocesses,
  dynamic libraries, device access, network access, artifact execution, or
  host-path leakage.
- Documentation states whether the field is an assumption, a capability claim,
  or a measured artifact.
- The manifest passes Manifest Claim Review when it makes specialized,
  approximate, calibration, or broad operation-family claims.
