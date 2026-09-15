#include <cuda_runtime.h>
#include "inputs.h"
#include "policy.h"
#include "kernels.cuh"
#include "fma.cuh"
#define TUC_TARGET "cuda"
#define TUC_BASELINE_CODE_DIGEST TUC_CUDA_CODE_DIGEST
#define TUC_FMA_CODE_DIGEST TUC_FMA_CUDA_CODE_DIGEST
static float *buffers[4] = {};
static constexpr unsigned int sizes[4] = {
  TUC_ROWS * TUC_INNER * 4U, TUC_INNER * TUC_COLUMNS * 4U,
  TUC_ROWS * TUC_COLUMNS * 4U, TUC_ROWS * 4U
};
static bool target_ready() {
  int count = 0;
  cudaDeviceProp prop = {};
  return sizeof(float) == 4U && cudaGetDeviceCount(&count) == cudaSuccess && count == 1 &&
         cudaGetDeviceProperties(&prop, 0) == cudaSuccess && prop.major == 8 && prop.minor == 6 &&
         cudaSetDevice(0) == cudaSuccess;
}
static bool prepare() {
  for (unsigned int i = 0; i < 4U; ++i)
    if (cudaMalloc(reinterpret_cast<void **>(&buffers[i]), sizes[i]) != cudaSuccess) return false;
  return true;
}
static bool finish() {
  bool ok = true;
  for (unsigned int i = 0; i < 4U; ++i) {
    if (buffers[i] != nullptr) ok = (cudaFree(buffers[i]) == cudaSuccess) && ok;
    buffers[i] = nullptr;
  }
  return ok;
}
static bool evaluate(bool fused, const float *a, const float *b, float *output,
                     unsigned int *calls) {
  if (cudaMemcpy(buffers[0], a, sizes[0], cudaMemcpyHostToDevice) != cudaSuccess ||
      cudaMemcpy(buffers[1], b, sizes[1], cudaMemcpyHostToDevice) != cudaSuccess ||
      cudaMemset(buffers[2], 0xff, sizes[2]) != cudaSuccess ||
      cudaMemset(buffers[3], 0xff, sizes[3]) != cudaSuccess) return false;
#ifdef TUC_SEPARATE_AS_FMA
  fused = false;
#endif
  unsigned int projection_blocks = TUC_PROJECTION_BLOCKS, output_blocks = TUC_OUTPUT_BLOCKS;
#ifdef TUC_INCOMPLETE_COVERAGE
  if (fused) { projection_blocks = 1U; output_blocks = 1U; }
#endif
  if (fused) tuc_projection_fma<<<projection_blocks, 32>>>(buffers[0], buffers[1], buffers[2]);
  else tuc_projection<<<projection_blocks, 32>>>(buffers[0], buffers[1], buffers[2]);
  ++*calls;
  if (cudaGetLastError() != cudaSuccess || cudaDeviceSynchronize() != cudaSuccess) return false;
  if (fused) tuc_sum_axis1_fma<<<output_blocks, 32>>>(buffers[2], buffers[3]);
  else tuc_sum_axis1<<<output_blocks, 32>>>(buffers[2], buffers[3]);
  ++*calls;
  if (cudaGetLastError() != cudaSuccess || cudaDeviceSynchronize() != cudaSuccess) return false;
  return cudaMemcpy(output, buffers[3], sizes[3], cudaMemcpyDeviceToHost) == cudaSuccess;
}
#include "common.h"
