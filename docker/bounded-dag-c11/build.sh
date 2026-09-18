#!/bin/sh
set -eu
mkdir -p /out/static /out/sanitized
# The context generator owns exactly these twelve immutable cases. No discovery,
# external inputs, native plan parser, device code, plugins or runtime compilation.
set -- main.c cases/00/worker.c cases/01/worker.c cases/02/worker.c \
  cases/03/worker.c cases/04/worker.c cases/05/worker.c cases/06/worker.c \
  cases/07/worker.c cases/08/worker.c cases/09/worker.c cases/10/worker.c cases/11/worker.c
for fault in 0 1 2 3; do
  case "$fault" in
    0) name=proof ;;
    1) name=skip-operation ;;
    2) name=corrupt-output ;;
    3) name=missing-publication ;;
  esac
  gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
    -Wshadow -Wstrict-prototypes -D_FORTIFY_SOURCE=3 -ffp-contract=off \
    -fno-fast-math -fexcess-precision=standard -DTUC_DAG_FAULT="$fault" \
    -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \
    -fno-ident -frandom-seed=tuc-bounded-dag-v0 -static \
    -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now \
    "$@" -lm -o "/out/static/$name"
  test -z "$(readelf -d "/out/static/$name" | grep '(NEEDED)')"
  gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -ffp-contract=off \
    -fno-fast-math -fexcess-precision=standard -DTUC_DAG_FAULT="$fault" \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    "$@" -lm -o "/out/sanitized/$name"
done
