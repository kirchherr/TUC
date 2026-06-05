# Foundational Research And Source Baseline

TUC should be guided by primary sources wherever possible. This file captures
the baseline references that should shape long-term architecture, security, and
open-source operations.

## Compiler Architecture

### MLIR

Primary sources:

- MLIR documentation: https://mlir.llvm.org/docs/
- Defining dialects: https://mlir.llvm.org/docs/DefiningDialects/
- Dialects: https://mlir.llvm.org/docs/Dialects/
- Pass infrastructure: https://mlir.llvm.org/docs/PassManagement/
- Pass catalog: https://mlir.llvm.org/docs/Passes/

TUC implications:

- Model the compiler as explicit, inspectable lowering stages.
- Keep pass contracts narrow and testable.
- Treat dialect boundaries as ownership boundaries: TLIR for source intent,
  HAC-IR for hardware-agnostic compute constraints, HS-IR for backend-specific
  choices.
- Prefer deterministic IR dumps for testing and debugging.

### Triton

Primary source:

- Triton documentation: https://triton-lang.org/main/index

TUC implications:

- Preserve Triton-style developer ergonomics.
- Avoid claiming Triton compatibility without defined compatibility levels and
  tests.
- Treat Triton integration as a staged adapter effort, not a one-shot fork.

### PyTorch Compiler Stack

Primary sources:

- PyTorch `torch.compiler`: https://docs.pytorch.org/docs/stable/user_guide/torch_compiler/torch.compiler.html
- `torch.compile`: https://docs.pytorch.org/docs/stable/generated/torch.compile.html

TUC implications:

- PyTorch integration should wait until graph capture, fallback, recompilation,
  and backend behavior are explainable.
- TUC must keep graph breaks, unsupported operations, and fallback behavior
  visible.

## Secure Software Development

### Secure By Design And SSDF

Primary sources:

- CISA Secure by Design: https://www.cisa.gov/securebydesign
- CISA Secure by Design guidance: https://www.cisa.gov/resources-tools/resources/secure-by-design
- NIST SSDF SP 800-218: https://csrc.nist.gov/pubs/sp/800/218/final

TUC implications:

- Security ownership belongs to the project, not the user.
- Security requirements must be explicit in design docs and RFCs.
- Secure defaults matter: no dynamic plugin execution, no network access, no
  broad filesystem writes, and no unsafe fallback behavior by default.

### Compiler And Native-Code Security

Primary sources:

- LLVM Security Response Group: https://llvm.org/docs/Security.html
- LLVM libFuzzer: https://llvm.org/docs/LibFuzzer.html
- Clang AddressSanitizer: https://clang.llvm.org/docs/AddressSanitizer.html
- OSS-Fuzz: https://google.github.io/oss-fuzz/
- MITRE CWE-20 input validation: https://cwe.mitre.org/data/definitions/20.html
- SEI CERT C/C++ Coding Standards: https://www.sei.cmu.edu/library/sei-cert-c-and-c-coding-standards/

TUC implications:

- Treat parsers, IR deserializers, backend manifests, and runtime plan loaders as
  hostile input boundaries.
- Add fuzz targets before accepting complex serialized formats.
- Use ASan/UBSan for native parser/lowering code.
- Keep native code minimal and heavily tested.

## Supply Chain And Open Source Security

Primary sources:

- SLSA levels: https://slsa.dev/spec/v1.0/levels
- SLSA getting started: https://slsa.dev/get-started
- GitHub Actions hardening: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
- GitHub artifact attestations: https://docs.github.com/actions/concepts/security/artifact-attestations
- CodeQL action: https://github.com/github/codeql-action
- OpenSSF Scorecard: https://openssf.org/scorecard/

TUC implications:

- CI should default to read-only token permissions.
- Release workflows must be treated as privileged systems.
- Provenance and artifact attestations should be implemented before package
  releases.
- OpenSSF Scorecard and CodeQL are appropriate early hardening steps.

## Codex Skills Created For TUC

The following personal Codex skills were created under
`C:\Users\tkirchherr\.codex\skills`:

- `tuc-compiler-architecture`
- `tuc-secure-compiler`
- `tuc-supply-chain-security`

Use them for future architecture, compiler-security, and supply-chain tasks.
