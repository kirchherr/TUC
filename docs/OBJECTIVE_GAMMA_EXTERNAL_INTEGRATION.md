# Objective Gamma External Integration

Objective Gamma tests TUC at an installation boundary rather than through an
in-repository example.

## Research Question

Can a backend author consume a built TUC distribution through a stable public
interface, validate a hardware-neutral capability package, and obtain the same
deterministic planning-conformance result without importing TUC examples,
tests, or source-tree modules?

For Backend Integration Package v0, the answer is **PASS**.

## Installed Proof

The proof path is:

```text
built TUC wheel
    -> temporary isolated environment
    -> copied external consumer
    -> tuc.integration API
    -> tuc-backend-verify CLI
    -> identical deterministic PASS report
```

`scripts/verify_external_backend_consumer.py` performs the proof. It:

1. resolves explicit, non-symlink wheel, consumer, and source-root inputs and
   bounds the copied consumer tree by file count and total bytes;
2. requires the exact audited fixture file set and a pinned SHA-256 digest for
   `consumer.py` before executing it;
3. creates a temporary environment and exposes only the already installed,
   hash-locked runtime dependency location;
4. force-installs the built TUC wheel without resolving dependencies;
5. verifies that `tuc` resolves outside the source root;
6. copies `integration/objective_gamma` to the temporary workspace;
7. removes `PYTHONPATH`, disables user-site loading, and uses Python isolated
   mode for the API consumer; and
8. requires API and installed console-script output to equal the same golden
   report byte for byte.

`tests/test_public_backend_integration.py` builds a fresh wheel and runs this
proof as part of the standard test suite. The unchanged CI and release
workflows both run that suite. A successful proof is silent; any environment
escape, import failure, CLI omission, or report drift fails the test run.

## Public Contract

External consumers use:

```python
from tuc.integration import verify_backend_package

report = verify_backend_package("backend_package.v0.json")
assert report.integration_status == "PASS"
```

The installed CLI is:

```bash
tuc-backend-verify backend_package.v0.json
```

The API is versioned by
`BACKEND_INTEGRATION_PUBLIC_API_VERSION =
"tuc.backend_integration_public_api.v0"`. Rejected CLI inputs return exit code
2 and a fixed source-free error; untrusted paths, payloads, and parser details
are not echoed.

## Security Boundary

Objective Gamma preserves the Backend Integration Package v0 boundary:

- packages remain bounded plain JSON with exact schemas;
- no package discovery, dynamic import, native library, subprocess, network,
  device, generated artifact, or runtime execution is admitted;
- the consumer imports only the public `tuc.integration` module;
- a passing package cannot grant executable-backend permission; and
- the proof does not use repository `examples/` or `tests/` at runtime.

## Claim Boundary

This is Level 4 integration evidence for data-only capability declaration,
support diagnostics, and compiler planning. It does not prove an executable
plugin ABI, vendor code isolation, native lowering, physical device support,
performance parity, package publication, or third-party adoption.

Decision: `rfcs/0291-objective-gamma-external-integration.md`.
