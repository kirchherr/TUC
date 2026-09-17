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
        -fno-ident -frandom-seed=tuc-chain-v0 \
        -static -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now \
        "$@" "$source" host.c -lm -o "$output"
    test -z "$(readelf -d "$output" | grep '(NEEDED)')"
}
compile generated.c /out/proof
compile generated.c /out/schedule-fanout -DTUC_SCHEDULE_FAULT=8
compile generated.c /out/schedule-output -DTUC_SCHEDULE_FAULT=9
compile generated.c /out/skip-second-publish -DTUC_SKIP_SECOND_PUBLISH=1
compile generated.c /out/invalidate-shared -DTUC_INVALIDATE_SHARED=1
compile generated.c /out/clobber-shared -DTUC_CLOBBER_SHARED=1
compile generated.c /out/schedule-placement -DTUC_SCHEDULE_FAULT=7
compile generated.c /out/schedule-count -DTUC_SCHEDULE_FAULT=1
compile generated.c /out/schedule-slot -DTUC_SCHEDULE_FAULT=2
compile generated.c /out/schedule-space -DTUC_SCHEDULE_FAULT=3
compile generated.c /out/schedule-order -DTUC_SCHEDULE_FAULT=4
compile generated.c /out/schedule-size -DTUC_SCHEDULE_FAULT=5
compile generated.c /out/schedule-duplicate -DTUC_SCHEDULE_FAULT=6
compile generated.c /out/skip-publish -DTUC_SKIP_PUBLISH=1
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -ffp-contract=off \
    -fno-fast-math -fexcess-precision=standard \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    generated.c host.c -lm -o /out/sanitized
compile generated.c /out/over-budget -DTUC_OVER_BUDGET=1
compile generated.c /out/nonfinite -DTUC_NONFINITE=1
sed 's/value < 0.0F ? 0.0F : value/value/' generated.c > mutant.c
compile mutant.c /out/bypass-relu
sed 's/output\[row\] = value;/output[row] = value < 0.0F ? 0.0F : value;/' mutant.c > late.c
compile late.c /out/late-relu
sed 's/value += projection\[row \* 5U + column\];/value = projection[row * 5U + column];/' generated.c > mutant.c
compile mutant.c /out/missing-sum
sed 's/b\[inner \* 5U + column\]/b[inner + column]/' generated.c > mutant.c
compile mutant.c /out/wrong-stride
sed 's/index < 165U/index < 164U/' generated.c > mutant.c
compile mutant.c /out/incomplete-coverage
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer contract_test.c -o /out/contract-sanitized
