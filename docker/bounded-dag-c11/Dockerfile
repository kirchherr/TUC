# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM --platform=linux/amd64 gcc:14.2.0-bookworm@sha256:82549aa8f90ada3236a8be70c74543132a76662ef33f0c3271ed802b81584a82 AS build
ENV LANG=C LC_ALL=C SOURCE_DATE_EPOCH=0
WORKDIR /src
COPY common.h main.c build.sh ./
COPY cases/ ./cases/
RUN --network=none sh build.sh

FROM build AS sanitized
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/out/sanitized/proof"]

FROM scratch AS static
COPY --from=build --chmod=0555 /out/static/ /opt/tuc/
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/opt/tuc/proof"]
