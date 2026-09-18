#!/bin/sh
set -eu
mkdir -p /out/static /out/sanitized
# Fixed generated application and thirteen compile-time fault variants only.
# No runtime source, graph, tensor input, library loader or device interface.
for fault in 0 1 2 3 4 5 6 7 8 9 10 11 12 13; do
  if [ "$fault" = 0 ]; then name=proof; else name="fault$fault"; fi
  gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
    -Wshadow -Wstrict-prototypes -D_FORTIFY_SOURCE=3 -ffp-contract=off \
    -fno-fast-math -fexcess-precision=standard -DTUC_SOURCE_FAULT="$fault" \
    -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \
    -fno-ident -frandom-seed=tuc-installed-source-c11-v0 -static \
    -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now \
    generated.c worker.c -lm -o "/out/static/$name"
  readelf -d "/out/static/$name" > /out/dynamic.txt
  readelf -l "/out/static/$name" > /out/program-headers.txt
  if grep -q '(NEEDED)' /out/dynamic.txt || grep -q 'INTERP' /out/program-headers.txt; then
    exit 1
  fi
  gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
    -Wshadow -Wstrict-prototypes -ffp-contract=off -fno-fast-math \
    -fexcess-precision=standard -DTUC_SOURCE_FAULT="$fault" \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    generated.c worker.c -lm -o "/out/sanitized/$name"
done
