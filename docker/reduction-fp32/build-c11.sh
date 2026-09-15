#!/bin/sh
set -eu
mkdir -p /out
compile() {
    source=$1
    output=$2
    shift 2
    gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
        -Wshadow -Wstrict-prototypes -D_FORTIFY_SOURCE=3 -ffp-contract=off \
        -fno-fast-math -fexcess-precision=standard \
        -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \
        -fno-ident -frandom-seed=tuc-fp32-v0 \
        -static -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now \
        "$@" "$source" host.c -lm -o "$output"
    test -z "$(readelf -d "$output" | grep '(NEEDED)')"
}
compile generated.c /out/proof
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -ffp-contract=off \
    -fno-fast-math -fexcess-precision=standard \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    generated.c host.c -lm -o /out/sanitized
compile generated.c /out/over-budget -DTUC_OVER_BUDGET=1
compile generated.c /out/nonfinite -DTUC_NONFINITE=1
sed 's/value += projection\[row \* 5U + column\];/value = projection[row * 5U + column];/' generated.c > mutant.c
compile mutant.c /out/missing-sum
sed 's/b\[inner \* 5U + column\]/b[inner + column]/' generated.c > mutant.c
compile mutant.c /out/wrong-stride
sed 's/row < 33U/row < 32U/g' generated.c > mutant.c
compile mutant.c /out/incomplete-coverage
