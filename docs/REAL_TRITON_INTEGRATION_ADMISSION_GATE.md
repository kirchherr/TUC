# Real Triton Integration Admission Gate

Real Triton Integration Admission Gate v0 is the fail-closed checkpoint after
Triton Integration Readiness becomes data-only complete.

The gate binds:

- `triton_integration_readiness`;
- `external_frontend_package_conformance`;
- `real_triton_integration_threat_model`.

It emits only evidence IDs, SHA-256 metadata digests, blocked surfaces, future
gate IDs, counts, and fixed `false` execution flags.

## Contract

- Report schema:
  `schemas/real_triton_integration_admission_gate_report.v0.schema.json`
- Report schema version:
  `tuc.real_triton_integration_admission_gate_report.v0`
- Admission contract:
  `real_triton_integration_admission.data_only.v0`
- Example: `examples/real_triton_integration_admission_gate.py`
- Golden:
  `tests/golden/frontend/real_triton_integration_admission_gate_report.json`
- Tests: `tests/test_real_triton_integration_admission_gate.py`
- RFC: `rfcs/0244-real-triton-integration-admission-gate.md`
- Threat model: `docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md`
- First surface gate: `docs/SOURCE_INGESTION_QUARANTINE_GATE.md`
- First surface gate schema:
  `schemas/source_ingestion_quarantine_gate_report.v0.schema.json`
- First surface gate example: `examples/source_ingestion_quarantine_gate.py`
- Second surface gate: `docs/PACKAGE_IMPORT_SANDBOX_GATE.md`
- Second surface gate schema:
  `schemas/package_import_sandbox_gate_report.v0.schema.json`
- Second surface gate example: `examples/package_import_sandbox_gate.py`
- Third surface gate: `docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md`
- Third surface gate schema:
  `schemas/plugin_discovery_allowlist_gate_report.v0.schema.json`
- Third surface gate example: `examples/plugin_discovery_allowlist_gate.py`
- Fourth surface gate: `docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md`
- Fourth surface gate schema:
  `schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json`
- Fourth surface gate example: `examples/triton_jit_execution_sandbox_gate.py`
- Fifth surface gate: `docs/DEVICE_ACCESS_SANDBOX_GATE.md`
- Fifth surface gate schema:
  `schemas/device_access_sandbox_gate_report.v0.schema.json`
- Fifth surface gate example: `examples/device_access_sandbox_gate.py`

## Meaning

The current report has:

- `all_required_evidence_present = true`;
- `admitted = false`;
- `admission_status = blocked`;
- `admission_decision = blocked_until_surface_gates_exist`.

This is deliberate. Readiness proves that the review prerequisites exist. The
admission gate proves that the real execution surfaces are still closed.

## Blocked Surfaces

The gate fixes these fields to `false`:

- `direct_source_ingestion`;
- `frontend_package_import`;
- `plugin_discovery`;
- `triton_jit_execution`;
- `device_access`;
- `generated_artifact_execution`;
- `native_backend_execution`.

The report also records blocked entries for package import, Python import,
function-object inspection, dynamic library loading, network access, and
subprocess execution.

## Security Boundary

The admission report is digest-only. It must not contain source text, Python
source, function objects, host paths, command lines, environment variables,
device identifiers, runtime handles, backend artifacts, generated code, plugin
entrypoints, raw benchmark output, raw timing samples, or executable
permissions.

Real Triton integration can only advance by replacing one blocked surface at a
time with a dedicated gate that has its own RFC, threat model, negative tests,
resource limits, and sandbox evidence.

## First Surface Gate

[Source Ingestion Quarantine Gate](SOURCE_INGESTION_QUARANTINE_GATE.md) is the
first dedicated gate for one of the blocked surfaces listed here. It binds this
admission gate, Source-To-Intent Parser Gate, Triton Source Preflight, and
Triton Source Threat Model evidence by digest while keeping
`direct_source_ingestion = false` and preventing source-to-ComputeGraph,
source-to-HAC-IR, source-to-runtime-plan, Python import, function-object
inspection, JIT, and generated-artifact execution.

Entry point: `examples/source_ingestion_quarantine_gate.py`.
Schema: `schemas/source_ingestion_quarantine_gate_report.v0.schema.json`.

## Second Surface Gate

[Package Import Sandbox Gate](PACKAGE_IMPORT_SANDBOX_GATE.md) is the second
dedicated gate for one of the blocked surfaces listed here. It binds this
admission gate, External Frontend Package Conformance, and Source Ingestion
Quarantine evidence by digest while keeping `frontend_package_import = false`,
`python_import = false`, and preventing package code execution, entrypoint
discovery, network access, filesystem access, environment access, subprocesses,
dynamic libraries, plugin discovery, and Source Intent from import.

Entry point: `examples/package_import_sandbox_gate.py`.
Schema: `schemas/package_import_sandbox_gate_report.v0.schema.json`.

## Third Surface Gate

[Plugin Discovery Allowlist Gate](PLUGIN_DISCOVERY_ALLOWLIST_GATE.md) is the
third dedicated gate for one of the blocked surfaces listed here. It binds this
admission gate, External Frontend Package Conformance, and Package Import
Sandbox evidence by digest while keeping `plugin_discovery = false`,
`entrypoint_discovery = false`, and preventing registry scans, filesystem
scans, plugin code execution, frontend package import, Python import, network
access, subprocesses, dynamic libraries, device access, and capability claims
from plugin code.

Entry point: `examples/plugin_discovery_allowlist_gate.py`.
Schema: `schemas/plugin_discovery_allowlist_gate_report.v0.schema.json`.

## Fourth Surface Gate

[Triton JIT Execution Sandbox Gate](TRITON_JIT_EXECUTION_SANDBOX_GATE.md) is the
fourth dedicated gate for one of the blocked surfaces listed here. It binds this
admission gate, Source Ingestion Quarantine, Package Import Sandbox, and Plugin
Discovery Allowlist evidence by digest while keeping
`triton_jit_execution = false`, `kernel_launch = false`, and preventing
generated artifact execution, device access, kernel-cache access, backend
binary emission, package import, Python import, plugin discovery, network
access, subprocesses, and dynamic libraries.

Entry point: `examples/triton_jit_execution_sandbox_gate.py`.
Schema: `schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json`.

## Fifth Surface Gate

[Device Access Sandbox Gate](DEVICE_ACCESS_SANDBOX_GATE.md) is the fifth
dedicated gate for one of the blocked surfaces listed here. It binds this
admission gate and Triton JIT Execution Sandbox evidence by digest while
keeping `device_access = false`, `device_discovery = false`, and preventing
device enumeration, driver API calls, device handles, device memory allocation,
memory mapping, direct memory access, kernel launch, generated artifact
execution, subprocesses, and dynamic libraries.

Entry point: `examples/device_access_sandbox_gate.py`.
Schema: `schemas/device_access_sandbox_gate_report.v0.schema.json`.