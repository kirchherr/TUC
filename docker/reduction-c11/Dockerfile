# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM --platform=linux/amd64 gcc:14.2.0-bookworm@sha256:82549aa8f90ada3236a8be70c74543132a76662ef33f0c3271ed802b81584a82 AS build
ENV LANG=C LC_ALL=C SOURCE_DATE_EPOCH=0
WORKDIR /src
COPY generated.c generated.h inputs.h harness.c build.sh ./
RUN --network=none sh build.sh

FROM build AS sanitizer-tests
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/out/sanitized"]
CMD ["--preflight"]

FROM scratch AS mutation-tests
COPY --from=build --chmod=0555 /out/proof /out/missing-sum /out/accidental-relu /out/wrong-axis /opt/tuc/
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/opt/tuc/proof"]
CMD ["--preflight"]

FROM scratch AS runtime
COPY --from=build --chmod=0555 /out/proof /opt/tuc/proof
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/opt/tuc/proof"]
CMD ["--preflight"]
