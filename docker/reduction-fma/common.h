#ifndef TUC_FMA_COMMON_H
#define TUC_FMA_COMMON_H
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

struct counts { unsigned int baseline, fused, different; };
static const char *check_pair(unsigned int index, const float *baseline, const float *fused,
                              struct counts *total) {
  struct counts current = {0, 0, 0};
  for (unsigned int row = 0; row < TUC_ROWS; ++row) {
    const double left = (double)baseline[row], right = (double)fused[row];
    if (!isfinite(left) || !isfinite(right) ||
        left < TUC_LOWER[index][row] || left > TUC_UPPER[index][row] ||
        right < TUC_LOWER[index][row] || right > TUC_UPPER[index][row])
      return "numeric_contract_mismatch";
  }
  for (unsigned int row = 0; row < TUC_ROWS; ++row) {
    if (baseline[row] != TUC_SEPARATE_EXPECTED[index][row] ||
        fused[row] != TUC_FMA_EXPECTED[index][row]) return "execution_policy_mismatch";
    if ((double)baseline[row] != TUC_REFERENCE64[index][row]) ++current.baseline;
    if ((double)fused[row] != TUC_REFERENCE64[index][row]) ++current.fused;
    if (baseline[row] != fused[row]) ++current.different;
  }
  total->baseline += current.baseline;
  total->fused += current.fused;
  total->different += current.different;
  return "none";
}

static int emit(const char *mode, const char *reason, bool security, unsigned int passed,
                int failed, unsigned int calls, unsigned int bytes, struct counts total) {
  const bool ok = strcmp(reason, "none") == 0;
  const bool correct = ok && strcmp(mode, "execute") == 0 && passed == TUC_RUNS && total.different > 0U;
  printf("{\"schema_version\":\"tuc.bounded_fma_observation.v0\","
         "\"target\":\"%s\",\"mode\":\"%s\",\"status\":\"%s\",\"reason_code\":\"%s\","
         "\"source_intent_digest\":\"%s\",\"corpus_digest\":\"%s\","
         "\"baseline_contract_digest\":\"%s\",\"acceptance_intervals_digest\":\"%s\","
         "\"execution_policy_digest\":\"%s\",\"baseline_code_digest\":\"%s\",\"fma_code_digest\":\"%s\","
         "\"output_shape\":[%u],\"case_count\":%u,\"runs_passed\":%u,\"failed_run_index\":%d,"
         "\"generated_function_calls\":%u,\"scalar_checks\":%u,\"tensor_bytes\":%u,"
         "\"baseline_rounding_outputs\":%u,\"fma_rounding_outputs\":%u,\"different_outputs\":%u,"
         "\"security_boundary_passed\":%s,\"numeric_contract_passed\":%s,"
         "\"execution_policy_passed\":%s,\"repeated_baseline_passed\":%s,\"raw_values_serialized\":false}\n",
         TUC_TARGET, mode, ok ? "PASS" : "ERROR", reason, TUC_INTENT_DIGEST, TUC_CORPUS_DIGEST,
         TUC_CONTRACT_DIGEST, TUC_INTERVALS_DIGEST, TUC_EXECUTION_POLICY_DIGEST,
         TUC_BASELINE_CODE_DIGEST, TUC_FMA_CODE_DIGEST, TUC_ROWS, TUC_CASES, passed, failed,
         calls, passed * TUC_ROWS * 2U, bytes, total.baseline, total.fused, total.different,
         security ? "true" : "false", correct ? "true" : "false", correct ? "true" : "false",
         correct ? "true" : "false");
  return ok ? 0 : 1;
}

int main(int argc, char **argv) {
  alarm(15U);
  struct counts total = {0, 0, 0};
  const bool execute = argc == 2 && strcmp(argv[1], "--execute") == 0;
  const bool preflight = argc == 2 && strcmp(argv[1], "--preflight") == 0;
  const char *mode = execute ? "execute" : "preflight";
  if (!execute && !preflight) return emit("invalid", "invalid_invocation", false, 0, -1, 0, 0, total);
  if (!security_ok()) return emit(mode, "security_boundary_mismatch", false, 0, -1, 0, 0, total);
  if (!target_ready() || FLT_RADIX != 2 || FLT_MANT_DIG != 24 || DBL_MANT_DIG != 53 ||
      FLT_EVAL_METHOD != 0 || fegetround() != FE_TONEAREST)
    return emit(mode, "target_not_ready", true, 0, -1, 0, 0, total);
  if (preflight) return emit(mode, "none", true, 0, -1, 0, 0, total);
  unsigned int calls = 0U;
  if (!prepare()) {
    (void)finish();
    return emit(mode, "allocation_failed", true, 0, -1, 0, 0, total);
  }
  float baseline[TUC_ROWS] = {0}, fused[TUC_ROWS] = {0};
  float first_baseline[TUC_ROWS] = {0}, first_fused[TUC_ROWS] = {0};
  unsigned int passed = 0U;
  int failed = -1;
  const char *reason = "none";
  for (unsigned int run = 0; run < TUC_RUNS; ++run) {
    const unsigned int index = run < TUC_CASES ? run : 0U;
    if (!evaluate(false, TUC_A[index], TUC_B[index], baseline, &calls) ||
        !evaluate(true, TUC_A[index], TUC_B[index], fused, &calls)) reason = "execution_failed";
    else {
#ifdef TUC_OVER_BUDGET
      fused[0] = nextafterf((float)TUC_UPPER[index][0], INFINITY);
#endif
#ifdef TUC_NONFINITE
      fused[0] = INFINITY;
#endif
      reason = check_pair(index, baseline, fused, &total);
      if (run == 0U) {
        memcpy(first_baseline, baseline, sizeof(baseline));
        memcpy(first_fused, fused, sizeof(fused));
      } else if (run == TUC_CASES) {
        for (unsigned int row = 0; row < TUC_ROWS; ++row)
          if (first_baseline[row] != baseline[row] || first_fused[row] != fused[row])
            reason = "replay_mismatch";
      }
    }
    if (strcmp(reason, "none") != 0) { failed = (int)run; break; }
    ++passed;
  }
  if (strcmp(reason, "none") == 0 && total.different == 0U) reason = "difference_witness_missing";
  if (!finish()) reason = "cleanup_failed";
  return emit(mode, reason, true, passed, failed, calls, TUC_TENSOR_BYTES, total);
}
#endif
