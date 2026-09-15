#include "generated.h"
#include "inputs.h"
#include <math.h>
#include <stdbool.h>
#define TUC_TARGET "c11"
#define TUC_CODE_DIGEST TUC_C11_CODE_DIGEST
static float projection[TUC_ROWS * TUC_COLUMNS], activated[TUC_ROWS * TUC_COLUMNS];
static bool target_ready(void) { return sizeof(float) == 4U; }
static bool prepare(void) { return true; }
static bool finish(void) { return true; }
static bool evaluate(const float *a, const float *b, float *output, unsigned int *calls) {
  for (unsigned int i = 0; i < TUC_ROWS * TUC_COLUMNS; ++i) {
    projection[i] = NAN;
    activated[i] = NAN;
  }
  for (unsigned int i = 0; i < TUC_ROWS; ++i) output[i] = NAN;
  tuc_projection(a, b, projection);
  ++*calls;
  tuc_relu(projection, activated);
  ++*calls;
  tuc_sum_axis1(activated, output);
  ++*calls;
  return true;
}
#include "common.h"
