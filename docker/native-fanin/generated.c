#include "generated.h"
#include <stddef.h>

void tuc_projection(const float *a, const float *b, float *projection) {
  for (size_t row = 0; row < 33U; ++row) {
    for (size_t column = 0; column < 5U; ++column) {
      float value = 0.0F;
      for (size_t inner = 0; inner < 7U; ++inner) {
        value += a[row * 7U + inner] * b[inner * 5U + column];
      }
#ifdef TUC_MISSING_JOIN
      value = 0.0F;
#endif
      projection[row * 5U + column] = value;
    }
  }
}

void tuc_sum_axis1(const float *projection, float *output) {
  for (size_t row = 0; row < 33U; ++row) {
    float value = 0.0F;
    for (size_t column = 0; column < 5U; ++column) {
      value += projection[row * 5U + column];
    }
    output[row] = value;
  }
}

void tuc_relu_left(const float *input, float *output) {
  for (size_t index = 0; index < 231U; ++index) {
#ifdef TUC_INCOMPLETE_LEFT
    if (index == 230U) return;
#endif
    const float value = input[index];
#if defined(TUC_BYPASS_LEFT) || defined(TUC_BYPASS_BOTH)
    output[index] = value;
#else
    output[index] = value < 0.0F ? 0.0F : value;
#endif
  }
}

void tuc_relu_right(const float *input, float *output) {
  for (size_t index = 0; index < 35U; ++index) {
#ifdef TUC_INCOMPLETE_RIGHT
    if (index == 34U) return;
#endif
    const float value = input[index];
#if defined(TUC_BYPASS_RIGHT) || defined(TUC_BYPASS_BOTH)
    output[index] = value;
#else
    output[index] = value < 0.0F ? 0.0F : value;
#endif
  }
}
