#!/bin/sh
set -eu
mkdir -p /out
compile() {
    gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
        -Wshadow -Wstrict-prototypes -D_FORTIFY_SOURCE=3 -ffp-contract=off \
        -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \
        -fno-ident -frandom-seed=tuc-shape-v0 \
        -static -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now "$1" host.c -lm -o "$2"
    test -z "$(readelf -d "$2" | grep '(NEEDED)')"
}
compile generated.c /out/proof
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -ffp-contract=off \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    generated.c host.c -lm -o /out/sanitized
sed 's/value += projection\[row \* 5U + column\];/value = projection[row * 5U + column];/' generated.c > mutant.c
compile mutant.c /out/missing-sum
sed 's/b\[inner \* 5U + column\]/b[inner + column]/' generated.c > mutant.c
compile mutant.c /out/wrong-stride
sed 's/row < 33U/row < 32U/g' generated.c > mutant.c
compile mutant.c /out/incomplete-coverage
