#ifndef TUC_PORTFOLIO_COMMON_H
#define TUC_PORTFOLIO_COMMON_H
#include "vectors.h"
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

static bool reference_matches(unsigned int index, const float *output) {
  /* Contract B first in binary64, separately from emitted matmul loops. */
  for (unsigned int row = 0U; row < 4U; ++row) {
    double reference = 0.0;
    for (unsigned int k = 0U; k < 8U; ++k)
      reference += (double)TUC_A[index][row * 8U + k] *
                   ((double)TUC_B[index][k * 2U] + (double)TUC_B[index][k * 2U + 1U]);
    if (!isfinite(output[row]) || reference != (double)TUC_EXPECTED[index][row] ||
        (double)output[row] != reference) return false;
  }
  return true;
}

static int emit(const char *mode, const char *reason, bool security,
                unsigned int passed, int failed, unsigned int calls, unsigned int bytes) {
  const bool ok = strcmp(reason, "none") == 0;
  const bool correct = ok && strcmp(mode, "execute") == 0 && passed == TUC_RUN_COUNT;
  printf("{\"schema_version\":\"tuc.reduction_input_portfolio_observation.v0\","
         "\"target\":\"%s\",\"mode\":\"%s\",\"status\":\"%s\",\"reason_code\":\"%s\","
         "\"source_intent_digest\":\"%s\",\"code_digest\":\"%s\",\"corpus_digest\":\"%s\","
         "\"security_boundary_passed\":%s,\"case_count\":%u,\"cases_passed\":%u,"
         "\"failed_run_index\":%d,\"generated_function_calls\":%u,"
         "\"case_tensor_bytes\":%u,\"reference_correctness\":%s,"
         "\"repeated_baseline_passed\":%s,\"raw_values_serialized\":false}\n",
         TUC_TARGET, mode, ok ? "PASS" : "ERROR", reason, TUC_INTENT_DIGEST,
         TUC_CODE_DIGEST, TUC_CORPUS_DIGEST, security ? "true" : "false", TUC_CASE_COUNT,
         passed, failed, calls, bytes, correct ? "true" : "false", correct ? "true" : "false");
  return ok ? 0 : 1;
}

int main(int argc, char **argv) {
  alarm(15U);
  const bool execute = argc == 2 && strcmp(argv[1], "--execute") == 0;
  const bool preflight = argc == 2 && strcmp(argv[1], "--preflight") == 0;
  const char *mode = execute ? "execute" : "preflight";
  if (!execute && !preflight) return emit("invalid", "invalid_invocation", false, 0, -1, 0, 0);
  if (!security_ok()) return emit(mode, "security_boundary_mismatch", false, 0, -1, 0, 0);
  if (!target_ready()) return emit(mode, "target_not_ready", true, 0, -1, 0, 0);
  if (preflight) return emit(mode, "none", true, 0, -1, 0, 0);
  unsigned int calls = 0U;
  if (!prepare()) {
    (void)finish();
    return emit(mode, "allocation_failed", true, 0, -1, 0, 0);
  }
  float output[4] = {0};
  unsigned int passed = 0U;
  int failed = -1;
  const char *reason = "none";
  for (unsigned int run = 0U; run < TUC_RUN_COUNT; ++run) {
    const unsigned int index = run < TUC_CASE_COUNT ? run : 0U;
    if (!evaluate(TUC_A[index], TUC_B[index], output, &calls)) reason = "execution_failed";
    else if (!reference_matches(index, output)) reason = "reference_mismatch";
    if (strcmp(reason, "none") != 0) { failed = (int)run; break; }
    ++passed;
  }
  if (!finish()) reason = "cleanup_failed";
  return emit(mode, reason, true, passed, failed, calls, 240U);
}
#endif
