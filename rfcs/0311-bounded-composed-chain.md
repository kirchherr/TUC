# RFC 0311: Bounded Source-Derived Matmul, ReLU, Reduction

Status: Implemented; native observations pending acceptance

## Question and Scope

Can the same restricted source intent preserve the observable semantics of
`sum(ReLU(A @ B), axis=1)` through three generated stages on C11 CPU and CUDA
GPU targets? This is a composition experiment, not a new general backend.

The existing inert module ingress parses three assignments and a terminal store.
No Python module, import, decorator, or Triton kernel is executed. Exact intent
identity and typed dataflow are checked before composing the frozen RFC 0308
matmul and sum emitters with an explicit ReLU stage. Only shapes `(33,7)`, `(7,5)`,
two `(33,5)` intermediates, and output `(33,)` are admitted. Source spelling is
Triton-shaped research syntax, not a claim of runnable production Triton coverage.

The same payload also has a regression through metadata, ComputeGraph, HAC-IR,
capability planning, and trusted prototype execution. That float64-storage
prototype check is distinct from the native FP32 experiment. Native code is
emitted from the reviewed intent; it does not execute the core partition plan.

## Numerical Contract

For each row define exact rational binary32-input quantities:

```text
P[c] = sum_k A[k] B[k,c]
R    = sum_c max(P[c], 0)
S    = sum_k,c abs(A[k] B[k,c])
u    = 2^-24
gamma(n) = n*u / (1-n*u)
abs(observed - R) <= gamma(13) * S
```

Separate rounded products and sequential accumulation have at most eight
roundings along any matmul term. ReLU is 1-Lipschitz and exact on admitted
normal-or-zero binary32 values. Sequential five-column summation yields the
bound `(gamma(8) + gamma(5)*(1+gamma(8))) * S <= gamma(13)*S`.
No reassociation, automatic FMA contraction, fast math, overflow, underflow,
NaN input, or infinity input is admitted. Signed zeros compare numerically.

Unlike RFC 0309, the exact reference cannot contract B before applying ReLU.
The new reference computes every exact projection before clamping and summing.
Exact rational intervals are encoded with inward-rounded binary64 endpoints;
binary32-to-binary64 comparisons do not widen acceptance. A second integer-based
ties-even oracle checks the declared separate FP32 execution order. All its
intermediates must remain in the bounded normal-or-zero arithmetic domain.

The ten RFC 0309 input recipes are reused, with cancellation first. This first
case rejects both bypassed ReLU and ReLU moved after reduction outside the error
interval on every row. It is replayed after the other nine cases. The separate
and FMA evidence of RFC 0310 remains unchanged; FMA is not enabled in this chain.

## Execution and Security Exception

This is the dedicated native execution exception required by the proof artifact
review policy. Normal `execute_graph`, plugin admission, and source-ingestion
gates are unchanged. The pure verifier never starts native code or containers.

The trusted, reviewed operator script uses pinned GCC/CUDA images, a deny-default
build context, networkless build steps, and image-ID-bound execution. Runtime:
no network, no host mounts, read-only root, UID/GID 10001, all capabilities dropped,
no-new-privileges, default seccomp, private IPC, one CPU, 32 PIDs, 1 GiB RAM/swap
ceiling, 8 MiB noexec tmpfs, 64 descriptors, no core dump, no container log driver.
Worker alarm: 15 seconds; operator timeout: 30 seconds; build timeout: 600 seconds.
Cleanup targets only the operator's uniquely named container.

CUDA admits only one visible reviewed sm86 device and SASS-only compilation:
no PTX JIT, device cache, runtime source compiler, or kernel supplied by a caller.
Three synchronized launches use 6, 6, and 2 blocks of 32 threads. Five explicit
tensor allocations total 2516 bytes; partial allocation is cleaned up. Intermediate
and terminal buffers are poisoned before every run. ReLU preserves NaN poison
instead of hiding unwritten values; NaN remains outside admitted semantics.

Host security review and idle-GPU checks precede every operator GPU run. Container
limits do not constitute a VRAM limit or protect against a host driver fault.
The GPU driver remains an attack surface, and a timeout cannot recover a hung
driver. Do not share the experiment with unrelated workloads or modify services.

## Acceptance

- Both actual targets pass 10 cases plus first-case replay: 33 calls, 363 scalar
  checks each, and 256 outputs differ numerically from the rounded exact reference.
- Seven independently compiled controls fail on the first run: bypass ReLU, late
  ReLU, missing sum, wrong stride, incomplete ReLU coverage, over-budget value,
  and nonfinite value. None becomes a success record.
- C11 also passes address/undefined-behavior sanitizers. CUDA SASS inspection
  rejects unexpected FFMA in the projection and any PTX fallback.
- Records bind intent, corpus, numeric contract, emitted target code, full reviewed
  program-file set, and operator image ID. The accepted source commit is recorded.
- Public observations contain no tensor values, device IDs, paths, commands,
  timing, or runtime handles. Published fixed test vectors are fixtures, not
  observed user data. Operator records remain same-maintainer assertions, not
  cryptographic proof that an untrusted reporter executed the program.

Independent reproduction, arbitrary source/shapes/inputs, cross-vendor execution,
general chain lowering, production admission, and native performance remain
unproven. No Objective Alpha identity, HAC-IR golden, or old native record changes.
