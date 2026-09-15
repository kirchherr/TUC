#!/bin/sh
set -eu
mkdir -p /out

compile() {
    gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
        -Wshadow -Wstrict-prototypes -D_FORTIFY_SOURCE=3 -ffp-contract=off \
        -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \
        -fno-ident -frandom-seed=tuc-reduction-v0 \
        -static -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now \
        "$1" harness.c -lm -o "$2"
    test -z "$(readelf -d "$2" | grep '(NEEDED)')"
    readelf -h "$2" | grep -q 'Machine:.*Advanced Micro Devices X86-64'
}

compile generated.c /out/proof
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -ffp-contract=off \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    -fno-omit-frame-pointer generated.c harness.c -lm -o /out/sanitized

# Fixed wrong-code probes. All remain in bounds and must fail the same oracle.
sed 's/value += projection\[row \* 2U + column\];/value = projection[row * 2U + column];/' generated.c > missing_sum.c
sed 's/output\[row\] = value;/output[row] = value > 0.0F ? value : 0.0F;/' generated.c > accidental_relu.c
sed 's/projection\[row \* 2U + column\];/projection[column * 4U + row];/' generated.c > wrong_axis.c
compile missing_sum.c /out/missing-sum
compile accidental_relu.c /out/accidental-relu
compile wrong_axis.c /out/wrong-axis
