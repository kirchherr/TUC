#include <cuda_runtime.h>
#include "kernels.cuh"
#define TUC_TARGET "cuda"
#define TUC_CODE_DIGEST TUC_CUDA_CODE_DIGEST
static float *buffers[4] = {};
static bool target_ready() {
  int count = 0;
  cudaDeviceProp prop = {};
  return sizeof(float) == 4U && cudaGetDeviceCount(&count) == cudaSuccess && count == 1 &&
         cudaGetDeviceProperties(&prop, 0) == cudaSuccess && prop.major == 8 && prop.minor == 6 &&
         cudaSetDevice(0) == cudaSuccess;
}
static bool prepare() {
  constexpr unsigned int sizes[4] = {128U, 64U, 32U, 16U};
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
static bool evaluate(const float *a, const float *b, float *output, unsigned int *calls) {
  if (cudaMemcpy(buffers[0], a, 128U, cudaMemcpyHostToDevice) != cudaSuccess ||
      cudaMemcpy(buffers[1], b, 64U, cudaMemcpyHostToDevice) != cudaSuccess) return false;
  tuc_projection<<<1, 32>>>(buffers[0], buffers[1], buffers[2]);
  ++*calls;
  if (cudaGetLastError() != cudaSuccess || cudaDeviceSynchronize() != cudaSuccess) return false;
  tuc_sum_axis1<<<1, 32>>>(buffers[2], buffers[3]);
  ++*calls;
  if (cudaGetLastError() != cudaSuccess || cudaDeviceSynchronize() != cudaSuccess) return false;
  return cudaMemcpy(output, buffers[3], 16U, cudaMemcpyDeviceToHost) == cudaSuccess;
}
#include "common.h"
