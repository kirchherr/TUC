#!/bin/sh
set -eu
test "$(grep -c '__global__ void' kernels.cuh)" = 4
test -z "$(grep '__global__' device.cu)"
mkdir -p /out/bin
compile() {
    output=$1
    shift
    gcc -std=c11 -O2 -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off \
        -fexcess-precision=standard -fstack-protector-strong -fPIE -D_FORTIFY_SOURCE=3 \
        -Dtuc_projection=tuc_host_projection -Dtuc_relu_left=tuc_host_relu_left \
        -Dtuc_relu_right=tuc_host_relu_right -Dtuc_sum_axis1=tuc_host_sum_axis1 \
        "$@" -c generated.c -o host-kernels.o
    nvcc --std=c++17 -O2 --cudart=static --fmad=false --ftz=false \
        --generate-code=arch=compute_86,code=sm_86 \
        --compiler-options=-Wall,-Wextra,-Werror,-fno-fast-math,-ffp-contract=off,-fstack-protector-strong,-fPIE,-D_FORTIFY_SOURCE=3 \
        --linker-options=-pie,-z,relro,-z,now "$@" device.cu host-kernels.o -o "$output"
    test -n "$(cuobjdump --list-elf "$output" | grep sm_86)"
    test -z "$(cuobjdump --list-ptx "$output")"
}
. ./faults.sh
cuobjdump --dump-sass /out/bin/proof > /out/sass.txt
awk '/Function :/ {inside = ($0 ~ /tuc_projection/); if (inside) found=1} inside && /FFMA/ {bad=1} END {exit (!found || bad)}' /out/sass.txt
