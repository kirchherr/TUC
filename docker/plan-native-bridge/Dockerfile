# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM --platform=linux/amd64 gcc:14.2.0-bookworm@sha256:82549aa8f90ada3236a8be70c74543132a76662ef33f0c3271ed802b81584a82 AS c11-build
ENV LANG=C LC_ALL=C SOURCE_DATE_EPOCH=0
WORKDIR /src
COPY docker/plan-native-bridge/generated.c docker/plan-native-bridge/generated.h docker/plan-native-bridge/host.c ./
COPY docker/plan-native-bridge/inputs.h docker/plan-native-bridge/oracle.h docker/plan-native-bridge/common.h docker/plan-native-bridge/build-c11.sh ./
COPY docker/plan-native-bridge/dispatch_contract.h docker/plan-native-bridge/c11_dispatch.h ./
RUN --network=none sh build-c11.sh

FROM c11-build AS c11-sanitizer
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/out/sanitized"]
CMD ["--preflight"]

FROM scratch AS c11-runtime
COPY --from=c11-build --chmod=0555 /out/proof /out/bypass-relu /out/late-relu /out/missing-sum /out/wrong-stride /out/incomplete-coverage /out/over-budget /out/nonfinite /out/unknown-opcode /out/wrong-order /out/input-overwrite /out/missing-step /out/wrong-target /opt/tuc/
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/opt/tuc/proof"]
CMD ["--preflight"]

FROM --platform=linux/amd64 nvidia/cuda:12.8.1-devel-ubuntu24.04@sha256:4b9ed5fa8361736996499f64ecebf25d4ec37ff56e4d11323ccde10aa36e0c43 AS cuda-build
WORKDIR /src
COPY docker/plan-native-bridge/kernels.cuh docker/plan-native-bridge/device.cu ./
COPY docker/plan-native-bridge/inputs.h docker/plan-native-bridge/oracle.h docker/plan-native-bridge/common.h docker/plan-native-bridge/build-cuda.sh ./
COPY docker/plan-native-bridge/dispatch_contract.h docker/plan-native-bridge/cuda_dispatch.h ./
RUN --network=none sh build-cuda.sh

FROM --platform=linux/amd64 nvidia/cuda:12.8.1-runtime-ubuntu24.04@sha256:828c4d878adcaa4265d80c95d8ec877149b49bb2419a4cf3bb6aa889bbb7ca2e AS cuda-runtime
ENV CUDA_CACHE_DISABLE=1 CUDA_DISABLE_PTX_JIT=1 CUDA_VISIBLE_DEVICES=0 \
    NVIDIA_DRIVER_CAPABILITIES=compute NVIDIA_VISIBLE_DEVICES=0 LANG=C LC_ALL=C
COPY --from=cuda-build --chmod=0555 /out/proof /out/bypass-relu /out/late-relu /out/missing-sum /out/wrong-stride /out/incomplete-coverage /out/over-budget /out/nonfinite /out/unknown-opcode /out/wrong-order /out/input-overwrite /out/missing-step /out/wrong-target /opt/tuc/
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/opt/tuc/proof"]
CMD ["--preflight"]
