#!/bin/sh
set -eu
test "$(grep -c '__global__ void' kernels.cuh)" = 2
test "$(grep -c '__global__ void' fma.cuh)" = 2
test -z "$(grep '__global__' device.cu)"
mkdir -p /out
compile() {
    output=$1
    shift
    nvcc --std=c++17 -O2 --cudart=static --fmad=false --ftz=false \
        --generate-code=arch=compute_86,code=sm_86 \
        --compiler-options=-Wall,-Wextra,-Werror,-fno-fast-math,-ffp-contract=off,-fstack-protector-strong,-fPIE,-D_FORTIFY_SOURCE=3 \
        --linker-options=-pie,-z,relro,-z,now "$@" device.cu -o "$output"
    test -n "$(cuobjdump --list-elf "$output" | grep sm_86)"
    test -z "$(cuobjdump --list-ptx "$output")"
}
compile /out/proof
cuobjdump --dump-sass /out/proof > /out/sass.txt
awk '/Function :/ {inside = ($0 ~ /tuc_projection_fma/)} inside && /FFMA/ {found=1} END {exit !found}' /out/sass.txt
awk '/Function :/ {inside = ($0 ~ /tuc_projection/ && $0 !~ /tuc_projection_fma/); if (inside) found=1} inside && /FFMA/ {bad=1} END {exit (!found || bad)}' /out/sass.txt
compile /out/over-budget -DTUC_OVER_BUDGET=1
compile /out/nonfinite -DTUC_NONFINITE=1
compile /out/separate-as-fma -DTUC_SEPARATE_AS_FMA=1
compile /out/incomplete-coverage -DTUC_INCOMPLETE_COVERAGE=1
cp fma.cuh reviewed.cuh
sed 's/value += projection\[row \* 5U + column\];/value = projection[row * 5U + column];/' reviewed.cuh > fma.cuh
compile /out/missing-sum
sed 's/b\[inner \* 5U + column\]/b[inner + column]/' reviewed.cuh > fma.cuh
compile /out/wrong-stride
