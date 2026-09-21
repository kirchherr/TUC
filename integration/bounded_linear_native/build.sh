#!/bin/sh
set -eu
mkdir -p /out/static /out/sanitized
for fault in 0 1 2 3; do
  if [ "$fault" = 0 ]; then name=proof; else name="fault$fault"; fi
  gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
    -Wshadow -Wstrict-prototypes -D_FORTIFY_SOURCE=3 -ffp-contract=off \
    -fno-fast-math -frounding-math -fexcess-precision=standard -DTUC_LINEAR_FAULT="$fault" \
    -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \
    -fno-ident -frandom-seed=tuc-bounded-linear-v0 -static \
    -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now \
    nonsquare-entrypoint.c singleton-entrypoint.c mixed-entrypoint.c mlp-entrypoint.c worker.c \
    -lm -o "/out/static/$name"
  readelf -d "/out/static/$name" > /out/dynamic.txt
  readelf -l "/out/static/$name" > /out/program-headers.txt
  if grep -q '(NEEDED)' /out/dynamic.txt || grep -q 'INTERP' /out/program-headers.txt; then exit 1; fi
  gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
    -Wshadow -Wstrict-prototypes -ffp-contract=off -fno-fast-math \
    -frounding-math -fexcess-precision=standard -DTUC_LINEAR_FAULT="$fault" \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    nonsquare-entrypoint.c singleton-entrypoint.c mixed-entrypoint.c mlp-entrypoint.c worker.c \
    -lm -o "/out/sanitized/$name"
done
