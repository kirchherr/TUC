# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

FROM python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2

ARG USER_UID=10001
ARG USER_GID=10001

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONHASHSEED=0
ENV PYTHONNOUSERSITE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1

COPY requirements/source-worker.txt /tmp/source-worker.txt
RUN python -m pip install \
        --disable-pip-version-check \
        --no-cache-dir \
        --only-binary=:all: \
        --require-hashes \
        --requirement /tmp/source-worker.txt \
    && rm -f /tmp/source-worker.txt \
    && groupadd --gid "${USER_GID}" tuc-worker \
    && useradd \
        --uid "${USER_UID}" \
        --gid "${USER_GID}" \
        --no-create-home \
        --shell /usr/sbin/nologin \
        tuc-worker \
    && mkdir -p /opt/tuc/src /run/tuc \
    && chown -R "${USER_UID}:${USER_GID}" /opt/tuc /run/tuc

COPY --chown=${USER_UID}:${USER_GID} src/ /opt/tuc/src/

USER ${USER_UID}:${USER_GID}
WORKDIR /run/tuc

ENTRYPOINT ["python", "-I", "/opt/tuc/src/tuc/frontend/_isolated_source_ingestion_worker.py", "--oci"]
