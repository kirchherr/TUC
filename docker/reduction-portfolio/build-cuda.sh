#!/bin/sh
set -eu
test "$(grep -c '__global__ void' kernels.cuh)" = 2
test -z "$(grep '__global__' device.cu)"
mkdir -p /out
compile() {
    nvcc --std=c++17 -O2 --cudart=static --fmad=false \
        --generate-code=arch=compute_86,code=sm_86 \
        --compiler-options=-Wall,-Wextra,-Werror,-fstack-protector-strong,-fPIE,-D_FORTIFY_SOURCE=3 \
        --linker-options=-pie,-z,relro,-z,now device.cu -o "$1"
    test -n "$(cuobjdump --list-elf "$1" | grep sm_86)"
    test -z "$(cuobjdump --list-ptx "$1")"
}
compile /out/proof
cp kernels.cuh reviewed.cuh
sed 's/value += projection\[row \* 2U + column\];/value = projection[row * 2U + column];/' reviewed.cuh > kernels.cuh
compile /out/missing-sum
sed 's/output\[row\] = value;/output[row] = value > 0.0F ? value : 0.0F;/' reviewed.cuh > kernels.cuh
compile /out/accidental-relu
sed 's/projection\[row \* 2U + column\];/projection[column * 4U + row];/' reviewed.cuh > kernels.cuh
compile /out/wrong-axis
sed 's/output\[row\] = value;/const float frozen[4] = {-5.875F, 2.625F, 5.125F, 4.75F}; output[row] = value * 0.0F + frozen[row];/' reviewed.cuh > kernels.cuh
compile /out/frozen-output
