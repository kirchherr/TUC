# Installed Python model session consumer

Run `python -I consumer.py` for an inert candidate, or `python -I consumer.py --run`
to explicitly execute against an installed TUC wheel on Linux x86-64. Copy this
directory outside the checkout first. The caller needs the existing local Docker
daemon and private directory; no source-tree TUC imports are allowed.

Four sessions exercise Linear, Softmax, changed fixed parameters and a late
numeric failure. Expected observations: 21 successful calls, 42 scalar checks
(38 bitwise, four tolerance), 17 unchanged context snapshots, 20 invalid-extent
rejections and nine further lifecycle/input controls. Equations are independently
written with stdlib FP32 rounding. Repeated contexts bind directory inode and file
hashes locally; host paths are not retained in the receipt. Stable context checks
observe reuse, not throughput or resident native weights.

Only complete success writes `record.json` exclusively. The CI wrapper adds source,
wheel and consumer hashes. Synthetic lifecycle tests are not execution evidence.
