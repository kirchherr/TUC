#!/bin/sh
set -eu
mkdir -p /out/bin
compile() {
    output=$1
    shift
    gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
        -Wshadow -Wstrict-prototypes -D_FORTIFY_SOURCE=3 -ffp-contract=off \
        -fno-fast-math -fexcess-precision=standard \
        -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \
        -fno-ident -frandom-seed=tuc-fanin-v0 \
        -static -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now \
        "$@" generated.c host.c -lm -o "$output"
    test -z "$(readelf -d "$output" | grep '(NEEDED)')"
}
. ./faults.sh
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -ffp-contract=off \
    -fno-fast-math -fexcess-precision=standard \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    generated.c host.c -lm -o /out/sanitized
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    contract_test.c -o /out/contract-sanitized
