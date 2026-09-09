#include "generated.h"
#include "inputs.h"

#include <math.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

_Static_assert(sizeof(float) == 4U, "FP32 storage required");
_Static_assert((32U + 16U + 8U + 4U) * sizeof(float) == 240U,
               "bounded tensor working set required");

static bool security_ok(void) {
  if (getuid() != 10001U || getgid() != 10001U) {
    return false;
  }
  FILE *status = fopen("/proc/self/status", "r");
  if (status == NULL) {
    return false;
  }
  bool caps = false;
  bool privileges = false;
  bool seccomp = false;
  char line[256];
  size_t count = 0U;
  while (count++ < 1024U && fgets(line, sizeof(line), status) != NULL) {
    char value[32];
    int flag = -1;
    if (sscanf(line, "CapEff:%31s", value) == 1) {
      caps = strcmp(value, "0000000000000000") == 0;
    } else if (sscanf(line, "NoNewPrivs:%d", &flag) == 1) {
      privileges = flag == 1;
    } else if (sscanf(line, "Seccomp:%d", &flag) == 1) {
      seccomp = flag == 2;
    }
  }
  const bool closed = fclose(status) == 0;
  return closed && count < 1024U && caps && privileges && seccomp;
}

static bool reference_matches(const float *output) {
  /* Contract B first in binary64; do not repeat the emitted matmul loops. */
  static const double expected[4] = {-5.875, 2.625, 5.125, 4.75};
  for (size_t row = 0U; row < 4U; ++row) {
    double reference = 0.0;
    for (size_t k = 0U; k < 8U; ++k) {
      reference += (double)TUC_A[row * 8U + k] *
                   ((double)TUC_B[k * 2U] + (double)TUC_B[k * 2U + 1U]);
    }
    if (!isfinite(output[row]) || reference != expected[row] ||
        (double)output[row] != expected[row]) {
      return false;
    }
  }
  return true;
}

static int emit(const char *mode, bool passed, bool security,
                size_t calls, bool correct, const char *reason) {
  printf("{\"schema_version\":\"tuc.bounded_reduction_c11_observation.v0\","
         "\"status\":\"%s\",\"mode\":\"%s\",\"reason_code\":\"%s\","
         "\"source_intent_digest\":\"%s\",\"generated_source_digest\":\"%s\","
         "\"vector_digest\":\"%s\",\"generated_function_calls\":%zu,"
         "\"reference_correctness\":%s,\"security_boundary_passed\":%s,"
         "\"output_shape\":[4],\"working_set_bytes\":%u,"
         "\"raw_values_serialized\":false}\n",
         passed ? "PASS" : "ERROR", mode, reason, TUC_SOURCE_INTENT_DIGEST,
         TUC_GENERATED_SOURCE_DIGEST, TUC_VECTOR_DIGEST, calls,
         correct ? "true" : "false", security ? "true" : "false",
         calls == 2U ? 240U : 0U);
  return passed ? 0 : 1;
}

int main(int argc, char **argv) {
  alarm(5U);
  const bool execute = argc == 2 && strcmp(argv[1], "--execute") == 0;
  const bool preflight = argc == 2 && strcmp(argv[1], "--preflight") == 0;
  if (!execute && !preflight) {
    return emit("invalid", false, false, 0U, false, "invalid_invocation");
  }
  const char *mode = execute ? "execute" : "preflight";
  if (!security_ok()) {
    return emit(mode, false, false, 0U, false, "security_boundary_mismatch");
  }
  if (preflight) {
    return emit(mode, true, true, 0U, false, "none");
  }
  float projection[8] = {0.0F};
  float output[4] = {0.0F};
  tuc_projection(TUC_A, TUC_B, projection);
  tuc_sum_axis1(projection, output);
  if (!reference_matches(output)) {
    return emit(mode, false, true, 2U, false, "reference_mismatch");
  }
  return emit(mode, true, true, 2U, true, "none");
}
