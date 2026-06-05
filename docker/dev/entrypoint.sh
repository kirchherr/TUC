#!/usr/bin/env bash
set -euo pipefail

umask 0002

if [ "$#" -eq 0 ]; then
  exec bash
fi

exec "$@"
