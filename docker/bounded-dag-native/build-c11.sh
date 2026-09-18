#!/bin/sh
set -eu
mkdir -p /out/static /out/sanitized
# Compile fixed case wrappers only: each includes its byte-preserved generated.c.
# No filename discovery, plan parsing, source injection or compiler invocation at runtime.
set -- contract.c bindings.c corpora.c dispatch_host.c host.c \
  cases/00/host.c cases/01/host.c cases/02/host.c cases/03/host.c \
  cases/04/host.c cases/05/host.c cases/06/host.c cases/07/host.c \
  cases/08/host.c cases/09/host.c cases/10/host.c cases/11/host.c
for fault in 0 1 2 3; do
  if [ "$fault" = 0 ]; then name=proof; else name="fault$fault"; fi
  gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
    -Wshadow -Wstrict-prototypes -D_FORTIFY_SOURCE=3 -ffp-contract=off \
    -fno-fast-math -fexcess-precision=standard -DTUC_FAULT="$fault" \
    -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \
    -fno-ident -frandom-seed=tuc-bounded-dag-native-v0 -static \
    -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now \
    "$@" -lm -o "/out/static/$name"
  readelf -d "/out/static/$name" > "/out/dynamic-$name.txt"
  inspection_status=0
  grep -q '(NEEDED)' "/out/dynamic-$name.txt" || inspection_status=$?
  test "$inspection_status" = 1
  gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -ffp-contract=off \
    -fno-fast-math -fexcess-precision=standard -DTUC_FAULT="$fault" \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    "$@" -lm -o "/out/sanitized/$name"
done
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror \
  -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
  contract.c contract_test.c bindings.c -o /out/sanitized/contract-test
