# RFC 0327: Bounded CPU tensor addition and row bias

Status: implementation under validation; native observation pending.

## Problem and decision

RFC 0326 reaches native CPU execution from supported source text, but Matmul,
ReLU and row-Sum alone cannot express affine layers with learned biases or
residual additions. Add one hardware-neutral elementwise meaning, `add`, and
carry it through the existing source, JSON, metadata, HAC-IR, CPU application
and installed command interfaces. A two-layer MLP becomes five operations:
Matmul, Add, ReLU, Matmul, Add. No optimization or general broadcasting is added.

## Semantic contract

Source Intent uses `family=elementwise` and exactly the attribute
`elementwise_kind=add`; metadata/HAC-IR maps it to `kernel=add`. Add has exactly
two FP32 inputs and one output. Shapes must either be identical rank one/two,
or the left input is `[M,N]` and the right input is `[N]`. In both cases the
output has the left shape. The bias vector is indexed by column for every row.
Vector-plus-matrix reversal, `[M,1]`/`[1,N]` broadcasting, scalars, higher ranks
and implicit dtype promotion reject. Repeated input identity (`x+x`) is valid;
the output is a fresh SSA value.

The explicit source parser accepts only `result = left + right` where both
operands are known names. It reads an AST as data in the existing isolated
worker; no user operator dispatch, import, evaluation, call, index or nested
expression is introduced. Source Intent Intake and its JSON Schema extend the
existing fixed enum. Graph JSON still uses `source_intent.v0`; earlier values
and canonical documents retain their meaning.

Existing bounded limits remain: rank one/two, dimensions 1-64, eight operations,
24 tensors, checked work/storage budgets and required terminal returns. One
Add costs one scalar addition per output element. Movement accounting reads
the actual two operand extents and writes the output extent; it does not
materialize a broadcast tensor. Existing generic elementwise movement remains
unchanged for other kernels.

## Backend and numeric contract

The family stays `OperationKind.ELEMENTWISE`; capabilities and assignments use
the existing inspectable pipeline. The bounded Add emitter checks the selected
target explicitly and accepts only C11 CPU graphs. CUDA and mixed placement
reject before emission. This is a narrow backend constraint, not a new implicit
fallback. Existing family-level HAC `tuc.linearity=nonlinear` remains unchanged;
it is not a claim that mathematical addition is nonlinear.

The original RFC 0319 DAG and primitive emitter files are bound by historical
native receipts and remain byte-for-byte unchanged. Add-containing graphs use
the distinct `tuc.bounded_add_dag_artifacts.v0` manifest and a separate emitter.
Graphs without Add continue through the old path, preserving their emitted
bytes and original observations. CPU manifests distinguish `add` and
`add_row_bias`; the latter is an explicit shape-constrained implementation of
the same neutral intent. No CUDA Add source or launch support is claimed.

The checked C11 entrypoint uses its existing scalar addition helper: binary32,
round-to-nearest/ties-to-even, no contraction/reassociation, finite normal or
zero inputs/intermediates/outputs, and rejection of overflow or subnormal
results. Errors publish no numeric outputs. Existing alias, extent, rounding,
storage, frame and cleanup checks remain in force. The separate trusted
simulator reference supports Add under its existing FP64 policy; native
correctness is established by independent ordered FP32 comparisons.

## Validation and security

Boundary tests cover symbolic syntax, known tensors, arity, FP32 shape matching,
right-bias indexing, repeated input identity, JSON type/schema bounds, budget
limits, unsupported targets and mutation of compiler results. Existing unary
semantics and non-Add golden artifacts are regression checked.

An independent installed CLI consumer owns affine, MLP, residual and repeated
input programs, shape profiles and input corpora. It compares actual graphs
and values, hashes original inputs and binds observations to the installed
program/request identities. Negative controls cover unsupported syntax and
broadcasts; normal input pairs deliberately produce overflow or a subnormal
result and must reject without outputs. Fixed native harnesses exercise the
new C11 paths under ASan/UBSan and bounded malformed descriptor/count/extent cases.
Synthetic Python responses are never native observations.

The workflow remains read-only and uses existing pinned actions, images and
hash-locked dependencies. No new dynamic loader, plugin discovery, network
input, dependency, credential, package publication or GPU execution is added.
Source, signature, graph and execution resource budgets retain RFC 0325/0326
limits. Prior evidence and claim gates remain unchanged; source/parser defaults,
general Triton support and production admission remain separate.

Owner review and actual installed/native CI are required for acceptance.
