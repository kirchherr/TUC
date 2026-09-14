#!/bin/sh
set -eu
test "$(grep -c '__global__ void' kernels.cuh)" = 2
test -z "$(grep '__global__' device.cu)"
mkdir -p /out
compile() {
    output=$1
    shift
    nvcc --std=c++17 -O2 --cudart=static --fmad=false \
        --generate-code=arch=compute_86,code=sm_86 \
        --compiler-options=-Wall,-Wextra,-Werror,-fstack-protector-strong,-fPIE,-D_FORTIFY_SOURCE=3 \
        --linker-options=-pie,-z,relro,-z,now "$@" device.cu -o "$output"
    test -n "$(cuobjdump --list-elf "$output" | grep sm_86)"
    test -z "$(cuobjdump --list-ptx "$output")"
}
compile /out/proof
compile /out/incomplete-coverage -DTUC_INCOMPLETE_COVERAGE=1
cp kernels.cuh reviewed.cuh
sed 's/value += projection\[row \* 5U + column\];/value = projection[row * 5U + column];/' reviewed.cuh > kernels.cuh
compile /out/missing-sum
sed 's/b\[inner \* 5U + column\]/b[inner + column]/' reviewed.cuh > kernels.cuh
compile /out/wrong-stride
