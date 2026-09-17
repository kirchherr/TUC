#!/bin/sh
set -eu
test "$(grep -c '__global__ void' kernels.cuh)" = 3
test -z "$(grep '__global__' device.cu)"
mkdir -p /out
compile() {
    output=$1
    shift
    nvcc --std=c++17 -O2 --cudart=static --fmad=false --ftz=false \
        --generate-code=arch=compute_86,code=sm_86 \
        --compiler-options=-Wall,-Wextra,-Werror,-fno-fast-math,-ffp-contract=off,-fstack-protector-strong,-fPIE,-D_FORTIFY_SOURCE=3 \
        --linker-options=-pie,-z,relro,-z,now "$@" device.cu host-kernels.o -o "$output"
    test -n "$(cuobjdump --list-elf "$output" | grep sm_86)"
    test -z "$(cuobjdump --list-ptx "$output")"
}
gcc -std=c11 -O2 -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off -fexcess-precision=standard -fstack-protector-strong -fPIE -D_FORTIFY_SOURCE=3 -Dtuc_projection=tuc_host_projection -Dtuc_relu=tuc_host_relu -Dtuc_sum_axis1=tuc_host_sum_axis1 -c generated.c -o host-kernels.o
compile /out/proof
compile /out/schedule-count -DTUC_SCHEDULE_FAULT=1
compile /out/schedule-slot -DTUC_SCHEDULE_FAULT=2
compile /out/schedule-space -DTUC_SCHEDULE_FAULT=3
compile /out/schedule-order -DTUC_SCHEDULE_FAULT=4
compile /out/schedule-size -DTUC_SCHEDULE_FAULT=5
compile /out/schedule-duplicate -DTUC_SCHEDULE_FAULT=6
compile /out/skip-publish -DTUC_SKIP_PUBLISH=1
compile /out/skip-transfer -DTUC_SKIP_TRANSFER=1
cuobjdump --dump-sass /out/proof > /out/sass.txt
awk '/Function :/ {inside = ($0 ~ /tuc_projection/); if (inside) found=1} inside && /FFMA/ {bad=1} END {exit (!found || bad)}' /out/sass.txt
compile /out/over-budget -DTUC_OVER_BUDGET=1
compile /out/nonfinite -DTUC_NONFINITE=1
compile /out/incomplete-coverage -DTUC_INCOMPLETE_COVERAGE=1
cp kernels.cuh reviewed.cuh
sed 's/value < 0.0F ? 0.0F : value/value/' reviewed.cuh > bypass.cuh
cp bypass.cuh kernels.cuh
cp generated.c reviewed.c
sed 's/value < 0.0F ? 0.0F : value/value/' reviewed.c > generated.c
gcc -std=c11 -O2 -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off -fexcess-precision=standard -fstack-protector-strong -fPIE -D_FORTIFY_SOURCE=3 -Dtuc_projection=tuc_host_projection -Dtuc_relu=tuc_host_relu -Dtuc_sum_axis1=tuc_host_sum_axis1 -c generated.c -o host-kernels.o
compile /out/bypass-relu
sed 's/output\[row\] = value;/output[row] = value < 0.0F ? 0.0F : value;/' bypass.cuh > kernels.cuh
compile /out/late-relu
cp reviewed.c generated.c
gcc -std=c11 -O2 -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off -fexcess-precision=standard -fstack-protector-strong -fPIE -D_FORTIFY_SOURCE=3 -Dtuc_projection=tuc_host_projection -Dtuc_relu=tuc_host_relu -Dtuc_sum_axis1=tuc_host_sum_axis1 -c generated.c -o host-kernels.o
sed 's/value += projection\[row \* 5U + column\];/value = projection[row * 5U + column];/' reviewed.cuh > kernels.cuh
compile /out/missing-sum
sed 's/b\[inner \* 5U + column\]/b[inner + column]/' reviewed.cuh > kernels.cuh
compile /out/wrong-stride
