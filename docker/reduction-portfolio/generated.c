#include "generated.h"
#include <stddef.h>

void tuc_projection(const float *a, const float *b, float *projection) {
  for (size_t row = 0; row < 4U; ++row) {
    for (size_t column = 0; column < 2U; ++column) {
      float value = 0.0F;
      for (size_t inner = 0; inner < 8U; ++inner) {
        value += a[row * 8U + inner] * b[inner * 2U + column];
      }
      projection[row * 2U + column] = value;
    }
  }
}

void tuc_sum_axis1(const float *projection, float *output) {
  for (size_t row = 0; row < 4U; ++row) {
    float value = 0.0F;
    for (size_t column = 0; column < 2U; ++column) {
      value += projection[row * 2U + column];
    }
    output[row] = value;
  }
}
