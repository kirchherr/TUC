# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

FROM nvidia/cuda:12.8.1-devel-ubuntu24.04@sha256:4b9ed5fa8361736996499f64ecebf25d4ec37ff56e4d11323ccde10aa36e0c43 AS build

ARG TUC_GPU_OBSERVATION_SOURCE_DIGEST
ARG TUC_GPU_OBSERVATION_HEADER_DIGEST
ARG TUC_GPU_OBSERVATION_WORKLOAD_DIGEST

WORKDIR /src
COPY bounded_gpu_observation.cu objective_delta_workload.hpp objective_delta_workload.v0.json ./

RUN test "$(sha256sum bounded_gpu_observation.cu | cut -d ' ' -f 1)" = "${TUC_GPU_OBSERVATION_SOURCE_DIGEST#sha256:}" \
    && test "$(sha256sum objective_delta_workload.hpp | cut -d ' ' -f 1)" = "${TUC_GPU_OBSERVATION_HEADER_DIGEST#sha256:}" \
    && test "$(sha256sum objective_delta_workload.v0.json | cut -d ' ' -f 1)" = "${TUC_GPU_OBSERVATION_WORKLOAD_DIGEST#sha256:}" \
    && mkdir -p /out \
    && nvcc \
        --std=c++17 \
        --optimize=2 \
        --cudart=static \
        --generate-code=arch=compute_70,code=sm_70 \
        --compiler-options=-Wall,-Wextra,-Werror,-fstack-protector-strong,-fPIE,-D_FORTIFY_SOURCE=3 \
        --linker-options=-pie,-z,relro,-z,now \
        -DTUC_GPU_OBSERVATION_WORKLOAD_DIGEST=\"${TUC_GPU_OBSERVATION_WORKLOAD_DIGEST}\" \
        bounded_gpu_observation.cu \
        --output-file /out/tuc-bounded-gpu-observation \
    && test -n "$(cuobjdump --list-elf /out/tuc-bounded-gpu-observation | grep 'sm_70')" \
    && test -z "$(cuobjdump --list-ptx /out/tuc-bounded-gpu-observation)" \
    && strip --strip-unneeded /out/tuc-bounded-gpu-observation

FROM nvidia/cuda:12.8.1-runtime-ubuntu24.04@sha256:828c4d878adcaa4265d80c95d8ec877149b49bb2419a4cf3bb6aa889bbb7ca2e

ARG USER_UID=10001
ARG USER_GID=10001
ARG TUC_GPU_OBSERVATION_SOURCE_DIGEST
ARG TUC_GPU_OBSERVATION_HEADER_DIGEST
ARG TUC_GPU_OBSERVATION_WORKLOAD_DIGEST

LABEL org.opencontainers.image.source="https://github.com/kirchherr/TUC" \
      org.opencontainers.image.title="TUC bounded GPU observation" \
      org.opencontainers.image.version="research-v0" \
      io.tuc.gpu-observation.contract="bounded_gpu_observation.physical_device.v0" \
      io.tuc.gpu-observation.header-digest="${TUC_GPU_OBSERVATION_HEADER_DIGEST}" \
      io.tuc.gpu-observation.source-digest="${TUC_GPU_OBSERVATION_SOURCE_DIGEST}" \
      io.tuc.gpu-observation.workload-digest="${TUC_GPU_OBSERVATION_WORKLOAD_DIGEST}"

ENV CUDA_CACHE_DISABLE=1 \
    CUDA_DISABLE_PTX_JIT=1 \
    CUDA_VISIBLE_DEVICES=0 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    NVIDIA_DRIVER_CAPABILITIES=compute \
    NVIDIA_VISIBLE_DEVICES=0

RUN groupadd --gid "${USER_GID}" tuc-gpu-observation \
    && useradd \
        --uid "${USER_UID}" \
        --gid "${USER_GID}" \
        --no-create-home \
        --shell /usr/sbin/nologin \
        tuc-gpu-observation \
    && mkdir -p /opt/tuc/bin /opt/tuc/share /run/tuc \
    && chown "${USER_UID}:${USER_GID}" /run/tuc

COPY --from=build --chmod=0555 /out/tuc-bounded-gpu-observation /opt/tuc/bin/tuc-bounded-gpu-observation
COPY --chmod=0444 objective_delta_workload.v0.json /opt/tuc/share/objective_delta_workload.v0.json

USER ${USER_UID}:${USER_GID}
WORKDIR /run/tuc

ENTRYPOINT ["/opt/tuc/bin/tuc-bounded-gpu-observation"]
CMD ["--preflight"]
