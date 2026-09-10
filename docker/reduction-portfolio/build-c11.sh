#!/bin/sh
set -eu
mkdir -p /out
compile() {
    gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
        -Wshadow -Wstrict-prototypes -D_FORTIFY_SOURCE=3 -ffp-contract=off \
        -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \
        -fno-ident -frandom-seed=tuc-portfolio-v0 \
        -static -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now "$1" host.c -lm -o "$2"
    test -z "$(readelf -d "$2" | grep '(NEEDED)')"
}
compile generated.c /out/proof
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -ffp-contract=off \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    generated.c host.c -lm -o /out/sanitized
sed 's/value += projection\[row \* 2U + column\];/value = projection[row * 2U + column];/' generated.c > mutant.c
compile mutant.c /out/missing-sum
sed 's/output\[row\] = value;/output[row] = value > 0.0F ? value : 0.0F;/' generated.c > mutant.c
compile mutant.c /out/accidental-relu
sed 's/projection\[row \* 2U + column\];/projection[column * 4U + row];/' generated.c > mutant.c
compile mutant.c /out/wrong-axis
sed 's/output\[row\] = value;/const float frozen[4] = {-5.875F, 2.625F, 5.125F, 4.75F}; output[row] = value * 0.0F + frozen[row];/' generated.c > mutant.c
compile mutant.c /out/frozen-output
