# Security Policy

TUC is pre-alpha and not ready for production use.

## Supported Versions

No released version is currently supported.

## Reporting Issues

For now, report security-sensitive issues privately to the repository owner or
maintainer team. Use GitHub private vulnerability reporting when it is enabled
for the repository; otherwise contact the repository owner directly.

Do not publish exploit details in public issues before maintainers have had a
chance to assess the problem.

## Security Baseline

TUC follows the project baseline in
[docs/SECURITY_BASELINE.md](docs/SECURITY_BASELINE.md). Compiler inputs,
serialized IR, backend metadata, plugin manifests, caches, and runtime plans are
treated as untrusted until validated.
