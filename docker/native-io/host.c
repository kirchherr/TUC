#include "generated.h"
#include "inputs.h"
#include <math.h>
#include <stddef.h>
#define TUC_TARGET "c11"
#define TUC_CODE_DIGEST TUC_C11_CODE_DIGEST
#define TUC_NATIVE_TARGET 1U
#define TUC_DISPATCH_HEADER "c11_dispatch.h"
#define TUC_IO_HEADER "c11_io.h"
#include "dispatch_contract.h"
#include "io_contract.h"
static float projection[TUC_ROWS * TUC_COLUMNS], activated[TUC_ROWS * TUC_COLUMNS];
static bool target_ready(void) { return io_valid() && sizeof(float) == 4U; }
static bool prepare(void) { return true; }
static bool finish(void) { return true; }
static bool evaluate(const float *a, const float *b, float *output, unsigned int *calls) {
  for (unsigned int i = 0; i < TUC_ROWS * TUC_COLUMNS; ++i) {
    projection[i] = NAN;
    activated[i] = NAN;
  }
  for (unsigned int i = 0; i < TUC_ROWS; ++i) output[i] = NAN;
  const float *host[2] = {a, b};
  const float *read[5] = {NULL, NULL, projection, activated, output};
  float *write[5] = {NULL, NULL, projection, activated, output};
  unsigned int completed = 0U;
  for (unsigned int i = 0U; i < TUC_IO_COUNT; ++i) {
    const struct tuc_io_step s = io_step(i);
    if (s.phase != 1U) continue;
    read[s.slot] = host[s.slot];
    ++completed; ++io_completed; ++io_bindings;
  }
  if (completed != 2U) return false;
  for (unsigned int i = 0; i < TUC_STEP_COUNT; ++i) {
    const struct tuc_step s = plan_step(i);
    switch (s.opcode) {
      case 1U: tuc_projection(read[s.a], read[s.b], write[s.out]); break;
      case 2U: tuc_relu(read[s.a], write[s.out]); break;
      case 3U: tuc_sum_axis1(read[s.a], write[s.out]); break;
      default: return false;
    }
    ++*calls;
  }
  for (unsigned int i = 0U; i < TUC_IO_COUNT; ++i) {
    const struct tuc_io_step s = io_step(i);
    if (s.phase != 2U) continue;
#ifdef TUC_IO_SKIP_OUTPUT
    continue;
#endif
    if (read[s.slot] != output) return false;
    ++completed; ++io_completed; ++io_bindings;
  }
  return completed == 3U;
}
#include "common.h"
