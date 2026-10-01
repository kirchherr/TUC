# Bounded CPU Model Session Audit

This directory contains a standalone Python-standard-library audit of the fixed
model-session receipt retained at
`docs/evidence/bounded-model-session-36570752112.json`.

Run it from any directory with Python 3.11 or newer:

```text
python -I audit_receipt.py bounded-model-session-36570752112.json
```

The auditor imports neither TUC nor NumPy. It reads one bounded regular JSON
file, recomputes three model digests and all 21 request digests, reconstructs
all 42 scalar results with explicit binary32 rounding, and checks the retained
source, wheel, consumer, program and receipt identities. It has no network,
subprocess, native-code, plugin, device or filesystem-write path.

A passing audit checks one already observed receipt. It is not a second native
execution and is not independent organizational reproduction.
