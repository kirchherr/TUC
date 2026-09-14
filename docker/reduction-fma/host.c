#include "generated.h"
#include "fma.h"
#include "inputs.h"
#include "policy.h"
#include <math.h>
#include <stdbool.h>
#define TUC_TARGET "c11"
#define TUC_BASELINE_CODE_DIGEST TUC_C11_CODE_DIGEST
#define TUC_FMA_CODE_DIGEST TUC_FMA_C11_CODE_DIGEST
static float projection[TUC_ROWS * TUC_COLUMNS];
static bool target_ready(void) { return sizeof(float) == 4U; }
static bool prepare(void) { return true; }
static bool finish(void) { return true; }
static bool evaluate(bool fused, const float *a, const float *b, float *output,
                     unsigned int *calls) {
  for (unsigned int i = 0; i < TUC_ROWS * TUC_COLUMNS; ++i) projection[i] = NAN;
  for (unsigned int i = 0; i < TUC_ROWS; ++i) output[i] = NAN;
#ifdef TUC_SEPARATE_AS_FMA
  fused = false;
#endif
  if (fused) tuc_projection_fma(a, b, projection);
  else tuc_projection(a, b, projection);
  ++*calls;
  if (fused) tuc_sum_axis1_fma(projection, output);
  else tuc_sum_axis1(projection, output);
  ++*calls;
  return true;
}
#include "common.h"
