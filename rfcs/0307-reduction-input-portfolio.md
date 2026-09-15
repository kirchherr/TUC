# RFC 0307: Reduction Input Portfolio

## Status

Implemented and natively observed on 2026-09-10; merge review pending.
C11 and physical sm86 CUDA each passed all twenty cases plus replay and all
four wrong-code probes. C11 also passed ASan/UBSan. Both frozen-output mutants
passed the old baseline and failed at the next vector. Accepted records and
the tested source identity are listed in `docs/REDUCTION_INPUT_PORTFOLIO.md`.

## Decision

Keep the accepted Source Intent and generated C11/CUDA functions unchanged.
Extend the fixed input contract to twenty reviewed vectors and replay the
baseline after all other cases in the same process. Compile once per target,
reuse buffers, compare every output to the same exact reference and require
42 generated calls per target. The finite quarter-integer domain avoids
confusing input coverage with an unreviewed floating-point tolerance policy.

Add a frozen-output negative control that passes the previous single-vector
test but fails the second vector. Preserve the three existing wrong-code
controls and run the entire C11 portfolio with ASan/UBSan.

## Alternatives And Limits

Recompiling for every vector weakens the evidence that one executable handles
different inputs. Random unbounded floats complicate the numeric contract
before testing data independence. Dynamic input ingestion and new shapes are
separate security and compiler boundaries and are deliberately excluded.

No changes to the normal runtime, backend admission, source ingestion,
dependencies or old accepted evidence. This remains same-maintainer research,
not an independent reproduction or a general input correctness proof.

See `docs/REDUCTION_INPUT_PORTFOLIO.md` for the procedure and threat boundaries.
