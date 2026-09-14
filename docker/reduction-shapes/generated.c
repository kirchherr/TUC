#include "generated.h"
#include <stddef.h>

void tuc_projection(const float *a, const float *b, float *projection) {
  for (size_t row = 0; row < 33U; ++row) {
    for (size_t column = 0; column < 5U; ++column) {
      float value = 0.0F;
      for (size_t inner = 0; inner < 7U; ++inner) {
        value += a[row * 7U + inner] * b[inner * 5U + column];
      }
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
