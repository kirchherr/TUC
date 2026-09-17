# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM --platform=linux/amd64 gcc:14.2.0-bookworm@sha256:82549aa8f90ada3236a8be70c74543132a76662ef33f0c3271ed802b81584a82 AS c11-build
ENV LANG=C LC_ALL=C SOURCE_DATE_EPOCH=0
WORKDIR /src
COPY docker/native-placements/generated.c docker/native-placements/generated.h docker/native-placements/host.c ./
COPY docker/native-placements/inputs.h docker/native-placements/oracle.h docker/native-placements/common.h docker/native-placements/build-c11.sh ./
COPY docker/native-placements/plans.h docker/native-placements/worker.h docker/native-placements/contract.h ./
COPY docker/native-placements/contract_test.c ./
RUN --network=none sh build-c11.sh

FROM c11-build AS c11-sanitizer
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/out/sanitized"]
CMD ["ccc", "--preflight"]

FROM scratch AS c11-runtime
COPY --from=c11-build --chmod=0555 /out/proof /out/schedule-placement /out/bypass-relu /out/late-relu /out/missing-sum /out/wrong-stride /out/incomplete-coverage /out/over-budget /out/nonfinite /out/schedule-count /out/schedule-slot /out/schedule-space /out/schedule-order /out/schedule-size /out/schedule-duplicate /out/skip-publish /opt/tuc/
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/opt/tuc/proof"]
CMD ["ccc", "--preflight"]

FROM --platform=linux/amd64 nvidia/cuda:12.8.1-devel-ubuntu24.04@sha256:4b9ed5fa8361736996499f64ecebf25d4ec37ff56e4d11323ccde10aa36e0c43 AS cuda-build
WORKDIR /src
COPY docker/native-placements/kernels.cuh docker/native-placements/device.cu ./
COPY docker/native-placements/inputs.h docker/native-placements/oracle.h docker/native-placements/common.h docker/native-placements/build-cuda.sh ./
COPY docker/native-placements/plans.h docker/native-placements/worker.h docker/native-placements/contract.h ./
COPY docker/native-placements/generated.c docker/native-placements/generated.h ./
RUN --network=none sh build-cuda.sh

FROM --platform=linux/amd64 nvidia/cuda:12.8.1-runtime-ubuntu24.04@sha256:828c4d878adcaa4265d80c95d8ec877149b49bb2419a4cf3bb6aa889bbb7ca2e AS cuda-runtime
ENV CUDA_CACHE_DISABLE=1 CUDA_DISABLE_PTX_JIT=1 CUDA_VISIBLE_DEVICES=0 \
    NVIDIA_DRIVER_CAPABILITIES=compute NVIDIA_VISIBLE_DEVICES=0 LANG=C LC_ALL=C
COPY --from=cuda-build --chmod=0555 /out/proof /out/schedule-placement /out/skip-transfer /out/bypass-relu /out/late-relu /out/missing-sum /out/wrong-stride /out/incomplete-coverage /out/over-budget /out/nonfinite /out/schedule-count /out/schedule-slot /out/schedule-space /out/schedule-order /out/schedule-size /out/schedule-duplicate /out/skip-publish /opt/tuc/
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/opt/tuc/proof"]
CMD ["ccc", "--preflight"]
