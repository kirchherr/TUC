#!/bin/sh
set -eu
mkdir -p /out/bin /out/objects
# Only these fixed, generated wrappers supply primitives. Reuse their objects
# across fault variants; TUC_FAULT affects the reviewed device worker only.
set --
for source in contract.c bindings.c corpora.c dispatch_host.c \
  cases/00/host.c cases/01/host.c cases/02/host.c cases/03/host.c \
  cases/04/host.c cases/05/host.c cases/06/host.c cases/07/host.c \
  cases/08/host.c cases/09/host.c cases/10/host.c cases/11/host.c; do
  object="/out/objects/host-$#.o"
  gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
    -Wshadow -Wstrict-prototypes -fno-fast-math -ffp-contract=off \
    -fexcess-precision=standard -fstack-protector-strong -fPIE -D_FORTIFY_SOURCE=3 \
    -c "$source" -o "$object"
  set -- "$@" "$object"
done
for source in dispatch_device.cu \
  cases/00/device.cu cases/01/device.cu cases/02/device.cu cases/03/device.cu \
  cases/04/device.cu cases/05/device.cu cases/06/device.cu cases/07/device.cu \
  cases/08/device.cu cases/09/device.cu cases/10/device.cu cases/11/device.cu; do
  object="/out/objects/device-$#.o"
  nvcc --std=c++17 -O2 --fmad=false --ftz=false \
    --generate-code=arch=compute_86,code=sm_86 \
    --compiler-options=-Wall,-Wextra,-Werror,-fno-fast-math,-ffp-contract=off,-fstack-protector-strong,-fPIE,-D_FORTIFY_SOURCE=3 \
    -c "$source" -o "$object"
  set -- "$@" "$object"
done
for fault in 0 1 2 3 4; do
  if [ "$fault" = 0 ]; then name=proof; else name="fault$fault"; fi
  nvcc --std=c++17 -O2 --cudart=static --fmad=false --ftz=false \
    --generate-code=arch=compute_86,code=sm_86 -DTUC_FAULT="$fault" \
    --compiler-options=-Wall,-Wextra,-Werror,-fno-fast-math,-ffp-contract=off,-fstack-protector-strong,-fPIE,-D_FORTIFY_SOURCE=3 \
    --linker-options=-pie,-z,relro,-z,now device.cu "$@" -o "/out/bin/$name"
  # Inspection failures must fail the build, never masquerade as absent PTX.
  cuobjdump --list-elf "/out/bin/$name" > "/out/elf-$name.txt"
  grep -q sm_86 "/out/elf-$name.txt"
  cuobjdump --list-ptx "/out/bin/$name" > "/out/ptx-$name.txt"
  test ! -s "/out/ptx-$name.txt"
done
cuobjdump --dump-sass /out/bin/proof > /out/sass.txt
inspection_status=0
grep -Eq '[[:space:]](FFMA|HFMA2|DFMA)([[:space:].])' /out/sass.txt || inspection_status=$?
test "$inspection_status" = 1
