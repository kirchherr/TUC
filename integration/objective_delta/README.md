# Objective Delta Installed Compute Consumer

This directory is a standalone consumer for TUC's bounded installed portable-
compute proof. It contains one neutral Source Intent payload, two data-only
backend packages, one public-API consumer, and one expected metadata-only
report.

The verification harness copies this directory outside the repository, installs
the built TUC wheel into an isolated environment, and requires the Python API
and installed CLI to reproduce `expected_report.json` byte for byte.

No backend code, plugin entry point, source text, runtime handle, device path,
generated artifact, or raw tensor value is present or authorized.
