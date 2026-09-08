#include "generated_compiler_emitted_c11_functions.h"

#include <stddef.h>

void tuc_projection_matmul_4x8x2_f32(const float *a, const float *b,
                                     float *projection) {
  for (size_t row = 0; row < 4U; ++row) {
    for (size_t column = 0; column < 2U; ++column) {
      float value = 0.0F;
      for (size_t inner = 0; inner < 8U; ++inner) {
        value += a[(row * 8U) + inner] * b[(inner * 2U) + column];
      }
      projection[(row * 2U) + column] = value;
    }
  }
}

void tuc_activated_relu_4x2_f32(const float *projection, float *activated) {
  for (size_t index = 0; index < 8U; ++index) {
    const float value = projection[index];
    activated[index] = value > 0.0F ? value : 0.0F;
  }
}
