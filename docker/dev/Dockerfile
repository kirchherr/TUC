# syntax=docker/dockerfile:1.7

FROM ubuntu:26.04

ARG DEBIAN_FRONTEND=noninteractive
ARG PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ARG INSTALL_TORCH=1
ARG USERNAME=tuc
ARG USER_UID=10001
ARG USER_GID=10001

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV VIRTUAL_ENV=/opt/tuc-venv
ENV PATH="/opt/tuc-venv/bin:/usr/lib/llvm-18/bin:${PATH}"
ENV CC=clang-18
ENV CXX=clang++-18
ENV LLVM_CONFIG=/usr/bin/llvm-config-18
ENV LLVM_DIR=/usr/lib/llvm-18/lib/cmake/llvm
ENV MLIR_DIR=/usr/lib/llvm-18/lib/cmake/mlir
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        ccache \
        clang-18 \
        clang-tools-18 \
        cmake \
        curl \
        gdb \
        git \
        lld-18 \
        lldb-18 \
        llvm-18 \
        llvm-18-dev \
        llvm-18-tools \
        libmlir-18-dev \
        mlir-18-tools \
        ninja-build \
        pkg-config \
        python-is-python3 \
        python3 \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-venv \
        python3-wheel \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" -m "${USERNAME}" \
    && mkdir -p /workspace /opt/tuc-venv \
    && chown -R "${USERNAME}:${USERNAME}" /workspace /opt/tuc-venv

COPY requirements/dev.txt /tmp/tuc-requirements-dev.txt

RUN python -m venv "${VIRTUAL_ENV}" \
    && "${VIRTUAL_ENV}/bin/python" -m pip install --upgrade pip setuptools wheel \
    && if [ "${INSTALL_TORCH}" = "1" ]; then \
        "${VIRTUAL_ENV}/bin/python" -m pip install --index-url "${PYTORCH_INDEX_URL}" torch torchvision torchaudio; \
    fi \
    && "${VIRTUAL_ENV}/bin/python" -m pip install -r /tmp/tuc-requirements-dev.txt \
    && chown -R "${USERNAME}:${USERNAME}" "${VIRTUAL_ENV}" "/home/${USERNAME}" \
    && rm -f /tmp/tuc-requirements-dev.txt

COPY docker/dev/entrypoint.sh /usr/local/bin/tuc-entrypoint
RUN chmod +x /usr/local/bin/tuc-entrypoint

USER "${USERNAME}"
WORKDIR /workspace

ENTRYPOINT ["tuc-entrypoint"]
CMD ["bash"]
