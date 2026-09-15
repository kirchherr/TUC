#include "generated.h"
#include <stdbool.h>
#define TUC_TARGET "c11"
#define TUC_CODE_DIGEST TUC_C11_CODE_DIGEST
static float projection[8];
static bool target_ready(void) { return sizeof(float) == 4U; }
static bool prepare(void) { return true; }
static bool finish(void) { return true; }
static bool evaluate(const float *a, const float *b, float *output, unsigned int *calls) {
  tuc_projection(a, b, projection);
  ++*calls;
  tuc_sum_axis1(projection, output);
  ++*calls;
  return true;
}
#include "common.h"
