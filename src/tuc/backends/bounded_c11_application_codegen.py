"""Private fixed-frame application source generation; no native execution."""

from __future__ import annotations

import re

DOCKERFILE = (
    "# syntax=docker/dockerfile:1.7@sha256:"
    "a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e\n"
    "FROM --platform=linux/amd64 gcc:14.2.0-bookworm@sha256:"
    "82549aa8f90ada3236a8be70c74543132a76662ef33f0c3271ed802b81584a82 AS build\n"
    """ENV LANG=C LC_ALL=C SOURCE_DATE_EPOCH=0
WORKDIR /src
COPY entrypoint.c entrypoint.h application.c application.h build.sh ./
RUN --network=none sh build.sh

FROM build AS sanitized
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/out/sanitized/application"]

FROM scratch AS static
COPY --from=build --chmod=0555 /out/static/application /opt/tuc/application
USER 10001:10001
WORKDIR /run/tuc
ENTRYPOINT ["/opt/tuc/application"]
""")

DOCKERIGNORE = """**
!Dockerfile
!Dockerfile.dockerignore
!entrypoint.c
!entrypoint.h
!application.c
!application.h
!build.sh
"""

BUILD_SH = """#!/bin/sh
set -eu
mkdir -p /out/static /out/sanitized
gcc -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wformat=2 \\
  -Wshadow -Wstrict-prototypes -D_FORTIFY_SOURCE=3 -ffp-contract=off \\
  -fno-fast-math -frounding-math -fexcess-precision=standard \\
  -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \\
  -fno-ident -frandom-seed=tuc-bounded-c11-application-v0 -static \\
  -Wl,--build-id=none,-z,noexecstack,-z,relro,-z,now \\
  entrypoint.c application.c -lm -o /out/static/application
readelf -d /out/static/application > /out/dynamic.txt
readelf -l /out/static/application > /out/program-headers.txt
if grep -q '(NEEDED)' /out/dynamic.txt || grep -q 'INTERP' /out/program-headers.txt; then
  exit 1
fi
gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror -Wconversion -Wformat=2 \\
  -Wshadow -Wstrict-prototypes -ffp-contract=off -fno-fast-math \\
  -frounding-math -fexcess-precision=standard \\
  -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \\
  entrypoint.c application.c -lm -o /out/sanitized/application
"""


def emit_application(
    symbol: str, input_elements: tuple[int, ...], output_elements: tuple[int, ...],
    program_digest: str,
) -> tuple[str, str]:
    """Emit fixed-sized buffers and calls; user names never enter C text."""
    if (type(symbol) is not str or len(symbol) != 76 or
            re.fullmatch(r"tuc_c11_[0-9a-f]{64}_run", symbol) is None or
            type(program_digest) is not str or len(program_digest) != 64 or
            re.fullmatch(r"[0-9a-f]{64}", program_digest) is None):
        raise ValueError("bounded C11 application symbol rejected")
    for elements in (input_elements, output_elements):
        if (type(elements) is not tuple or not 1 <= len(elements) <= 24 or
                any(type(value) is not int or not 1 <= value <= 4096 for value in elements)):
            raise ValueError("bounded C11 application extents rejected")
    payload_bytes = sum(input_elements) * 4
    output_bytes = sum(output_elements) * 4
    if payload_bytes + output_bytes > 262144:
        raise ValueError("bounded C11 application payload budget rejected")
    request_bytes, response_bytes = 72 + payload_bytes, 76 + output_bytes
    header = f"""#ifndef TUC_C11_APPLICATION_V0_H
#define TUC_C11_APPLICATION_V0_H
#include <stddef.h>
#define TUC_APPLICATION_REQUEST_BYTES {request_bytes}U
#define TUC_APPLICATION_RESPONSE_BYTES {response_bytes}U
#define TUC_APPLICATION_ERROR_RESPONSE_BYTES 76U
#define TUC_APPLICATION_PROGRAM_DIGEST "{program_digest}"
/* One application per executable. Caller provides live, disjoint request,
 * response and response_size storage; capacity covers the declared byte count.
 * Invalid frames return 2 with size 0. C11 errors return 1 with only a header.
 * The request digest is an opaque echo here; the Python host verifies it. */
#ifdef __cplusplus
extern "C" {{
#endif
int tuc_application_process(const unsigned char *request, size_t request_size,
                            unsigned char *response, size_t response_capacity,
                            size_t *response_size);
#ifdef __cplusplus
}}
#endif
#endif
"""
    program = ", ".join(f"0x{program_digest[i:i + 2]}U" for i in range(0, 64, 2))
    lines = [
        '#include "application.h"', '#include "entrypoint.h"',
        "#include <stdint.h>", "#include <string.h>", "#include <limits.h>",
        "#ifndef TUC_APPLICATION_NO_MAIN", "#include <stdio.h>", "#include <unistd.h>", "#endif",
        '_Static_assert(CHAR_BIT == 8 && sizeof(float) == 4, "binary32 bytes required");',
        f"static const unsigned char tuc_program[32] = {{{program}}};",
        "static const unsigned char tuc_input_magic[8] = {'T','U','C','I','N','0','0','1'};",
        "static const unsigned char tuc_output_magic[8] = {'T','U','C','O','U','T','0','1'};",
        "static uint32_t tuc_load_u32(const unsigned char *data) {",
        "  return (uint32_t)data[0] | ((uint32_t)data[1] << 8) |",
        "         ((uint32_t)data[2] << 16) | ((uint32_t)data[3] << 24);", "}",
        "static void tuc_store_u32(unsigned char *data, uint32_t value) {",
        "  data[0] = (unsigned char)(value & UINT32_C(255));",
        "  data[1] = (unsigned char)((value >> 8) & UINT32_C(255));",
        "  data[2] = (unsigned char)((value >> 16) & UINT32_C(255));",
        "  data[3] = (unsigned char)((value >> 24) & UINT32_C(255));", "}",
        "int tuc_application_process(const unsigned char *request, size_t request_size,",
        "                            unsigned char *response, size_t response_capacity,",
        "                            size_t *response_size) {",
        "  if (response_size == NULL) return 2;", "  *response_size = 0U;",
        "  if (request == NULL || response == NULL ||",
        "      request_size != TUC_APPLICATION_REQUEST_BYTES ||",
        "      response_capacity < TUC_APPLICATION_RESPONSE_BYTES) return 2;",
        "  if (memcmp(request, tuc_input_magic, 8U) != 0 ||",
        "      memcmp(request + 8U, tuc_program, 32U) != 0) return 2;",
        "  unsigned char request_digest[32]; memcpy(request_digest, request + 40U, 32U);",
    ]
    for index, count in enumerate(input_elements):
        lines.append(f"  float input_{index}[{count}];")
    for index, count in enumerate(output_elements):
        lines.append(f"  float output_{index}[{count}];")
    offset = 72
    for index, count in enumerate(input_elements):
        lines += [f"  for (size_t i = 0; i < {count}U; ++i) {{",
                  f"    const uint32_t bits = tuc_load_u32(request + {offset}U + 4U * i);",
                  f"    memcpy(&input_{index}[i], &bits, sizeof(bits));", "  }"]
        offset += count * 4
    lines += [f"  const struct tuc_c11_input inputs[{len(input_elements)}] = {{",
              *(f"    {{input_{i}, {count}U}}," for i, count in enumerate(input_elements)), "  };",
              f"  const struct tuc_c11_output outputs[{len(output_elements)}] = {{",
              *(f"    {{output_{i}, {count}U}}," for i, count in enumerate(output_elements)),
              "  };",
              f"  const enum tuc_c11_status status = {symbol}(",
              f"      inputs, {len(input_elements)}U, outputs, {len(output_elements)}U);",
              "  if (status != TUC_C11_OK && status != TUC_C11_ARGUMENT &&",
              "      status != TUC_C11_NUMERIC && status != TUC_C11_ENVIRONMENT) return 2;",
              "  memcpy(response, tuc_output_magic, 8U); memcpy(response + 8U, tuc_program, 32U);",
              "  memcpy(response + 40U, request_digest, 32U);",
              "  tuc_store_u32(response + 72U, (uint32_t)status);",
              "  if (status != TUC_C11_OK) {",
              "    *response_size = TUC_APPLICATION_ERROR_RESPONSE_BYTES; return 1;", "  }"]
    offset = 76
    for index, count in enumerate(output_elements):
        lines += [f"  for (size_t i = 0; i < {count}U; ++i) {{", "    uint32_t bits;",
                  f"    memcpy(&bits, &output_{index}[i], sizeof(bits));",
                  f"    tuc_store_u32(response + {offset}U + 4U * i, bits);", "  }"]
        offset += count * 4
    lines += ["  *response_size = TUC_APPLICATION_RESPONSE_BYTES; return 0;", "}",
              "#ifndef TUC_APPLICATION_NO_MAIN", "int main(int argc, char **argv) {",
              "  (void)argv; if (argc != 1) return 2;", "  (void)alarm(5U);",
              "  unsigned char request[TUC_APPLICATION_REQUEST_BYTES + 1U];",
              "  unsigned char response[TUC_APPLICATION_RESPONSE_BYTES];",
              "  const size_t request_size = fread(request, 1U, sizeof(request), stdin);",
              "  if (ferror(stdin) || request_size != TUC_APPLICATION_REQUEST_BYTES ||",
              "      !feof(stdin)) return 2;",
              "  size_t response_size = 0U;",
              "  const int code = tuc_application_process(request, request_size, response,",
              "                                           sizeof(response), &response_size);",
              "  if (response_size != 0U &&",
              "      (fwrite(response, 1U, response_size, stdout) != response_size ||",
              "       fflush(stdout) != 0)) return 2;", "  return code;", "}", "#endif", ""]
    return header, "\n".join(lines)
