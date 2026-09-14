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
        -fno-ident -frandom-seed=tuc-fma-v0 \
        -static -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now \
        "$@" generated.c "$source" host.c -lm -o "$output"
    test -z "$(readelf -d "$output" | grep '(NEEDED)')"
}
compile fma.c /out/proof
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -ffp-contract=off \
    -fno-fast-math -fexcess-precision=standard \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    generated.c fma.c host.c -lm -o /out/sanitized
compile fma.c /out/over-budget -DTUC_OVER_BUDGET=1
compile fma.c /out/nonfinite -DTUC_NONFINITE=1
compile fma.c /out/separate-as-fma -DTUC_SEPARATE_AS_FMA=1
sed 's/value += projection\[row \* 5U + column\];/value = projection[row * 5U + column];/' fma.c > mutant.c
compile mutant.c /out/missing-sum
sed 's/b\[inner \* 5U + column\]/b[inner + column]/' fma.c > mutant.c
compile mutant.c /out/wrong-stride
sed 's/row < 33U/row < 32U/g' fma.c > mutant.c
compile mutant.c /out/incomplete-coverage
