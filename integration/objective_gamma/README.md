# Objective Gamma External Consumer

This directory is a standalone backend-author consumer for TUC's public,
data-only integration interface. It intentionally contains only:

- one backend package;
- one expected deterministic report; and
- one consumer importing `tuc.integration`.

TUC CI copies this directory outside the repository, installs the built TUC
wheel into a temporary environment, removes `PYTHONPATH`, enables Python
isolated mode, and runs both the Python API and the installed
`tuc-backend-verify` console script. Both paths must exactly match
`expected_report.json`.

The package declares capabilities and conformance cases only. It contains no
backend code and grants no execution permission.
