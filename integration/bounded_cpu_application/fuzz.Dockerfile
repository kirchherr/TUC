# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM --platform=linux/amd64 gcc:14.2.0-bookworm@sha256:82549aa8f90ada3236a8be70c74543132a76662ef33f0c3271ed802b81584a82
ENV LANG=C LC_ALL=C SOURCE_DATE_EPOCH=0
WORKDIR /src
COPY entrypoint.c entrypoint.h application.c application.h seed.h fuzz.c ./
RUN --network=none gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -Wconversion -Wformat=2 \
    -Wshadow -Wstrict-prototypes -ffp-contract=off -fno-fast-math -frounding-math \
    -fexcess-precision=standard -fsanitize=address,undefined -fno-sanitize-recover=all \
    -fno-omit-frame-pointer -DTUC_APPLICATION_NO_MAIN entrypoint.c application.c fuzz.c \
    -lm -o /opt/fuzz && \
    gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -Wconversion -ffp-contract=off \
    -fno-fast-math -frounding-math -fexcess-precision=standard \
    -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
    entrypoint.c application.c -lm -o /opt/application
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/opt/fuzz"]
