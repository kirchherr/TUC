#ifndef TUC_FP32_COMMON_H
#define TUC_FP32_COMMON_H
#include "inputs.h"
#include "oracle.h"
#include <fenv.h>
#include <float.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static bool security_ok(void) {
  if (getuid() != 10001U || getgid() != 10001U) return false;
  FILE *status = fopen("/proc/self/status", "r");
  if (status == NULL) return false;
  bool caps = false, privileges = false, seccomp = false;
  char line[256] = {0};
  unsigned int count = 0U;
  while (count++ < 1024U && fgets(line, sizeof(line), status) != NULL) {
    char value[32] = {0};
    int flag = -1;
    if (sscanf(line, "CapEff:%31s", value) == 1)
      caps = strcmp(value, "0000000000000000") == 0;
    else if (sscanf(line, "NoNewPrivs:%d", &flag) == 1) privileges = flag == 1;
    else if (sscanf(line, "Seccomp:%d", &flag) == 1) seccomp = flag == 2;
  }
  const bool closed = fclose(status) == 0;
  return closed && count < 1024U && caps && privileges && seccomp;
}

static bool reference_matches(unsigned int index, const float *output, unsigned int *rounded) {
  unsigned int count = 0U;
  for (unsigned int row = 0; row < TUC_ROWS; ++row) {
    /* FP32 -> FP64 is exact; inward endpoints cannot enlarge the rational budget. */
    const double value = (double)output[row];
    if (!isfinite(value) || value < TUC_LOWER[index][row] || value > TUC_UPPER[index][row])
      return false;
    if (value != TUC_REFERENCE64[index][row]) ++count;
  }
  *rounded += count;
  return true;
}

static int emit(const char *mode, const char *reason, bool security,
                unsigned int passed, int failed, unsigned int calls,
                unsigned int bytes, unsigned int rounded) {
  const bool ok = strcmp(reason, "none") == 0;
  const bool correct = ok && strcmp(mode, "execute") == 0 && passed == TUC_RUNS && rounded > 0U;
  printf("{\"schema_version\":\"tuc.bounded_reduction_fp32_observation.v0\","
         "\"target\":\"%s\",\"mode\":\"%s\",\"status\":\"%s\",\"reason_code\":\"%s\","
         "\"source_intent_digest\":\"%s\",\"code_digest\":\"%s\",\"corpus_digest\":\"%s\","
         "\"contract_digest\":\"%s\",\"output_shape\":[%u],\"security_boundary_passed\":%s,"
         "\"case_count\":%u,\"cases_passed\":%u,\"failed_run_index\":%d,"
         "\"generated_function_calls\":%u,\"tensor_bytes\":%u,"
         "\"outputs_differing_from_reference64\":%u,"
         "\"numeric_contract_passed\":%s,\"repeated_baseline_passed\":%s,"
         "\"raw_values_serialized\":false}\n",
         TUC_TARGET, mode, ok ? "PASS" : "ERROR", reason, TUC_INTENT_DIGEST,
         TUC_CODE_DIGEST, TUC_CORPUS_DIGEST, TUC_CONTRACT_DIGEST, TUC_ROWS,
         security ? "true" : "false", TUC_CASES, passed, failed, calls, bytes, rounded,
         correct ? "true" : "false", correct ? "true" : "false");
  return ok ? 0 : 1;
}

int main(int argc, char **argv) {
  alarm(15U);
  const bool execute = argc == 2 && strcmp(argv[1], "--execute") == 0;
  const bool preflight = argc == 2 && strcmp(argv[1], "--preflight") == 0;
  const char *mode = execute ? "execute" : "preflight";
  if (!execute && !preflight) return emit("invalid", "invalid_invocation", false, 0, -1, 0, 0, 0);
  if (!security_ok()) return emit(mode, "security_boundary_mismatch", false, 0, -1, 0, 0, 0);
  if (!target_ready() || FLT_RADIX != 2 || FLT_MANT_DIG != 24 || DBL_MANT_DIG != 53 ||
      FLT_EVAL_METHOD != 0 || fegetround() != FE_TONEAREST)
    return emit(mode, "target_not_ready", true, 0, -1, 0, 0, 0);
  if (preflight) return emit(mode, "none", true, 0, -1, 0, 0, 0);
  unsigned int calls = 0U;
  if (!prepare()) {
    (void)finish();
    return emit(mode, "allocation_failed", true, 0, -1, 0, 0, 0);
  }
  float output[TUC_ROWS] = {0};
  unsigned int passed = 0U, rounded = 0U;
  int failed = -1;
  const char *reason = "none";
  for (unsigned int run = 0; run < TUC_RUNS; ++run) {
    const unsigned int index = run < TUC_CASES ? run : 0U;
    if (!evaluate(TUC_A[index], TUC_B[index], output, &calls)) reason = "execution_failed";
    else {
#ifdef TUC_OVER_BUDGET
      output[0] = nextafterf((float)TUC_UPPER[index][0], INFINITY);
#endif
#ifdef TUC_NONFINITE
      output[0] = INFINITY;
#endif
      if (!reference_matches(index, output, &rounded)) reason = "numeric_contract_mismatch";
    }
    if (strcmp(reason, "none") != 0) { failed = (int)run; break; }
    ++passed;
  }
  if (strcmp(reason, "none") == 0 && rounded == 0U) reason = "rounding_witness_missing";
  if (!finish()) reason = "cleanup_failed";
  return emit(mode, reason, true, passed, failed, calls, TUC_TENSOR_BYTES, rounded);
}
#endif
