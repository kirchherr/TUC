# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM --platform=linux/amd64 nvidia/cuda:12.8.1-devel-ubuntu24.04@sha256:4b9ed5fa8361736996499f64ecebf25d4ec37ff56e4d11323ccde10aa36e0c43 AS build
WORKDIR /src
COPY kernels.cuh inputs.h cuda_digest.h harness.cu build.sh ./
RUN --network=none sh build.sh

FROM --platform=linux/amd64 nvidia/cuda:12.8.1-runtime-ubuntu24.04@sha256:828c4d878adcaa4265d80c95d8ec877149b49bb2419a4cf3bb6aa889bbb7ca2e AS runtime
ENV CUDA_CACHE_DISABLE=1 CUDA_DISABLE_PTX_JIT=1 CUDA_VISIBLE_DEVICES=0 \
    NVIDIA_DRIVER_CAPABILITIES=compute NVIDIA_VISIBLE_DEVICES=0 LANG=C LC_ALL=C
COPY --from=build --chmod=0555 /out/proof /opt/tuc/proof
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/opt/tuc/proof"]
CMD ["--preflight"]

FROM runtime AS mutation-tests
COPY --from=build --chmod=0555 /out/missing-sum /out/accidental-relu /out/wrong-axis /opt/tuc/
