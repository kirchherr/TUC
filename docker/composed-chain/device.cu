#include <cuda_runtime.h>
#include "inputs.h"
#include "kernels.cuh"
#define TUC_TARGET "cuda"
#define TUC_CODE_DIGEST TUC_CUDA_CODE_DIGEST
static float *buffers[5] = {};
static constexpr unsigned int sizes[5] = {
  TUC_ROWS * TUC_INNER * 4U, TUC_INNER * TUC_COLUMNS * 4U,
  TUC_ROWS * TUC_COLUMNS * 4U, TUC_ROWS * TUC_COLUMNS * 4U, TUC_ROWS * 4U
};
static bool target_ready() {
  int count = 0;
  cudaDeviceProp prop = {};
  return sizeof(float) == 4U && cudaGetDeviceCount(&count) == cudaSuccess && count == 1 &&
         cudaGetDeviceProperties(&prop, 0) == cudaSuccess && prop.major == 8 && prop.minor == 6 &&
         cudaSetDevice(0) == cudaSuccess;
}
static bool prepare() {
  for (unsigned int i = 0; i < 5U; ++i)
    if (cudaMalloc(reinterpret_cast<void **>(&buffers[i]), sizes[i]) != cudaSuccess) return false;
  return true;
}
static bool finish() {
  bool ok = true;
  for (unsigned int i = 0; i < 5U; ++i) {
    if (buffers[i] != nullptr) ok = (cudaFree(buffers[i]) == cudaSuccess) && ok;
    buffers[i] = nullptr;
  }
  return ok;
}
static bool synchronized() {
  return cudaGetLastError() == cudaSuccess && cudaDeviceSynchronize() == cudaSuccess;
}
static bool evaluate(const float *a, const float *b, float *output, unsigned int *calls) {
  if (cudaMemcpy(buffers[0], a, sizes[0], cudaMemcpyHostToDevice) != cudaSuccess ||
      cudaMemcpy(buffers[1], b, sizes[1], cudaMemcpyHostToDevice) != cudaSuccess) return false;
  for (unsigned int i = 2; i < 5U; ++i)
    if (cudaMemset(buffers[i], 0xff, sizes[i]) != cudaSuccess) return false;
  tuc_projection<<<TUC_PROJECTION_BLOCKS, 32>>>(buffers[0], buffers[1], buffers[2]);
  ++*calls;
  if (!synchronized()) return false;
  unsigned int relu_blocks = TUC_PROJECTION_BLOCKS;
#ifdef TUC_INCOMPLETE_COVERAGE
  relu_blocks = 1U;
#endif
  tuc_relu<<<relu_blocks, 32>>>(buffers[2], buffers[3]);
  ++*calls;
  if (!synchronized()) return false;
  tuc_sum_axis1<<<TUC_OUTPUT_BLOCKS, 32>>>(buffers[3], buffers[4]);
  ++*calls;
  if (!synchronized()) return false;
  return cudaMemcpy(output, buffers[4], sizes[4], cudaMemcpyDeviceToHost) == cudaSuccess;
}
#include "common.h"
