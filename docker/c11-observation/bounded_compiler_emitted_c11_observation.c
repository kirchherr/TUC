#include "compiler_emitted_c11_workload.h"
#include "generated_compiler_emitted_c11_functions.h"

#include <math.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef TUC_C11_OBSERVATION_WORKLOAD_DIGEST
#error "TUC_C11_OBSERVATION_WORKLOAD_DIGEST must be supplied by the reviewed build"
#endif

enum {
  TUC_EXPECTED_UID = 10001,
  TUC_EXPECTED_GID = 10001,
};

static const float TUC_TOLERANCE = 1.0e-5F;
static const size_t TUC_WORKLOAD_BYTES =
    (TUC_C11_A_COUNT + TUC_C11_B_COUNT + (2U * TUC_C11_OUTPUT_COUNT)) *
    sizeof(float);
_Static_assert((32U + 16U + 8U + 8U) * sizeof(float) == 256U,
               "bounded C11 working set must remain 256 bytes");

struct SecurityObservation {
  bool status_read;
  bool effective_capabilities_zero;
  int no_new_privileges;
  int seccomp_mode;
};

static struct SecurityObservation read_security_observation(void) {
  struct SecurityObservation observation = {false, false, -1, -1};
  FILE *status = fopen("/proc/self/status", "r");
  if (status == NULL) {
    return observation;
  }

  char line[256] = {0};
  char capability_value[32] = {0};
  bool capability_seen = false;
  bool no_new_privileges_seen = false;
  bool seccomp_seen = false;
  size_t line_count = 0U;
  while (line_count < 1024U && fgets(line, sizeof(line), status) != NULL) {
    ++line_count;
    if (sscanf(line, "CapEff:%31s", capability_value) == 1) {
      capability_seen = true;
      observation.effective_capabilities_zero =
          strcmp(capability_value, "0000000000000000") == 0;
    } else if (sscanf(line, "NoNewPrivs:%d", &observation.no_new_privileges) ==
               1) {
      no_new_privileges_seen = true;
    } else if (sscanf(line, "Seccomp:%d", &observation.seccomp_mode) == 1) {
      seccomp_seen = true;
    }
  }
  const bool closed = fclose(status) == 0;
  observation.status_read = closed && capability_seen && no_new_privileges_seen &&
                            seccomp_seen && line_count < 1024U;
  return observation;
}

static bool security_boundary_passed(
    const struct SecurityObservation *observation) {
  return observation->status_read &&
         observation->effective_capabilities_zero &&
         observation->no_new_privileges == 1 && observation->seccomp_mode == 2 &&
         (int)getuid() == TUC_EXPECTED_UID &&
         (int)getgid() == TUC_EXPECTED_GID;
}

static bool manifest_reference_matches(void) {
  for (size_t row = 0U; row < TUC_C11_ROWS; ++row) {
    for (size_t column = 0U; column < TUC_C11_COLUMNS; ++column) {
      double value = 0.0;
      for (size_t inner = 0U; inner < TUC_C11_INNER; ++inner) {
        value += (double)TUC_C11_A[(row * TUC_C11_INNER) + inner] *
                 (double)TUC_C11_B[(inner * TUC_C11_COLUMNS) + column];
      }
      const double activated = value > 0.0 ? value : 0.0;
      const size_t index = (row * TUC_C11_COLUMNS) + column;
      if (fabs(activated - (double)TUC_C11_EXPECTED_OUTPUT[index]) >
          (double)TUC_TOLERANCE) {
        return false;
      }
    }
  }
  return true;
}

static bool output_matches_manifest(const float *output) {
  for (size_t index = 0U; index < TUC_C11_OUTPUT_COUNT; ++index) {
    if (!isfinite(output[index]) ||
        fabsf(output[index] - TUC_C11_EXPECTED_OUTPUT[index]) > TUC_TOLERANCE) {
      return false;
    }
  }
  return true;
}

static void emit_observation(const char *mode, const char *status,
                             const char *reason_code,
                             size_t generated_function_call_count,
                             size_t working_set_bytes,
                             const char *reference_check_status,
                             const struct SecurityObservation *security) {
  printf(
      "{\"architecture\":\"x86_64\","
      "\"binary_format\":\"elf64\","
      "\"cuda_dependency\":false,"
      "\"device_access\":false,"
      "\"dtype\":\"float32\","
      "\"environment_serialized\":false,"
      "\"generated_function_call_count\":%zu,"
      "\"generated_function_count\":2,"
      "\"hardware_identifiers_serialized\":false,"
      "\"mode\":\"%s\","
      "\"operation_families\":[\"matmul\",\"elementwise\"],"
      "\"protocol\":\"tuc.bounded_compiler_emitted_c11_worker.v0\","
      "\"raw_tensor_values_serialized\":false,"
      "\"raw_timing_samples_serialized\":false,"
      "\"reason_code\":\"%s\","
      "\"reference_check_status\":\"%s\","
      "\"security\":{"
      "\"effective_capabilities_zero\":%s,"
      "\"gid\":%d,"
      "\"no_new_privileges\":%d,"
      "\"seccomp_mode\":%d,"
      "\"status_read\":%s,"
      "\"uid\":%d},"
      "\"source_language\":\"c11\","
      "\"status\":\"%s\","
      "\"tensor_shape\":[4,2],"
      "\"workload_contract\":\"%s\","
      "\"workload_manifest_digest\":\"%s\","
      "\"working_set_bytes\":%zu}\n",
      generated_function_call_count, mode, reason_code, reference_check_status,
      security->effective_capabilities_zero ? "true" : "false", (int)getgid(),
      security->no_new_privileges, security->seccomp_mode,
      security->status_read ? "true" : "false", (int)getuid(), status,
      TUC_C11_WORKLOAD_CONTRACT, TUC_C11_OBSERVATION_WORKLOAD_DIGEST,
      working_set_bytes);
  fflush(stdout);
}

static int fail(const char *mode, const char *reason_code,
                size_t generated_function_call_count,
                const struct SecurityObservation *security) {
  emit_observation(mode, "ERROR", reason_code, generated_function_call_count,
                   0U, "not_executed", security);
  return 1;
}

int main(int argc, char **argv) {
  const bool preflight = argc == 2 && strcmp(argv[1], "--preflight") == 0;
  const bool execute = argc == 2 && strcmp(argv[1], "--execute") == 0;
  const char *mode = execute ? "execute" : "preflight";
  const struct SecurityObservation security = read_security_observation();

  if (!preflight && !execute) {
    return fail("invalid", "invalid_invocation", 0U, &security);
  }
  if (!security_boundary_passed(&security)) {
    return fail(mode, "security_boundary_mismatch", 0U, &security);
  }
  if (!manifest_reference_matches()) {
    return fail(mode, "workload_reference_mismatch", 0U, &security);
  }
  if (preflight) {
    emit_observation(mode, "PASS", "none", 0U, 0U, "not_executed",
                     &security);
    return 0;
  }

  float a[TUC_C11_A_COUNT];
  float b[TUC_C11_B_COUNT];
  float projection[TUC_C11_OUTPUT_COUNT] = {0.0F};
  float activated[TUC_C11_OUTPUT_COUNT] = {0.0F};
  memcpy(a, TUC_C11_A, sizeof(a));
  memcpy(b, TUC_C11_B, sizeof(b));

  tuc_projection_matmul_4x8x2_f32(a, b, projection);
  tuc_activated_relu_4x2_f32(projection, activated);
  if (!output_matches_manifest(activated)) {
    return fail(mode, "reference_mismatch", 2U, &security);
  }

  emit_observation(mode, "PASS", "none", 2U, TUC_WORKLOAD_BYTES, "passed",
                   &security);
  return 0;
}
