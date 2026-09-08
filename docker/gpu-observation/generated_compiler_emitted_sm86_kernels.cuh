#pragma once

#include <cuda_runtime.h>

namespace tuc::compiler_emitted_gpu {

inline constexpr int kThreadsPerBlock = 32;

__global__ void tuc_projection_matmul_4x8x2_f32(const float* a, const float* b,
                                                float* projection) {
  const int index = static_cast<int>(threadIdx.x);
  if (index >= static_cast<int>(kOutputElementCount)) {
    return;
  }
  const int row = index / static_cast<int>(kColumns);
  const int column = index % static_cast<int>(kColumns);
  float value = 0.0F;
  for (int inner = 0; inner < static_cast<int>(kInner); ++inner) {
    value += a[row * static_cast<int>(kInner) + inner] *
             b[inner * static_cast<int>(kColumns) + column];
  }
  projection[index] = value;
}

__global__ void tuc_activated_relu_4x2_f32(const float* projection,
                                            float* activated) {
  const int index = static_cast<int>(threadIdx.x);
  if (index >= static_cast<int>(kOutputElementCount)) {
    return;
  }
  const float value = projection[index];
  activated[index] = value > 0.0F ? value : 0.0F;
}

}  // namespace tuc::compiler_emitted_gpu
