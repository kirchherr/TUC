#include <cuda_runtime.h>
#include "inputs.h"
#include "kernels.cuh"
#define TUC_TARGET "cuda"
#define TUC_CODE_DIGEST TUC_CUDA_CODE_DIGEST
#define TUC_NATIVE_TARGET 2U
#define TUC_DISPATCH_HEADER "cuda_dispatch.h"
#define TUC_IO_HEADER "cuda_io.h"
#include "dispatch_contract.h"
#include "io_contract.h"
static float *buffers[5] = {};
static bool target_ready() {
  if (!io_valid()) return false;
  int count = 0;
  cudaDeviceProp prop = {};
  return sizeof(float) == 4U && cudaGetDeviceCount(&count) == cudaSuccess && count == 1 &&
         cudaGetDeviceProperties(&prop, 0) == cudaSuccess && prop.major == 8 && prop.minor == 6 &&
         cudaSetDevice(0) == cudaSuccess;
}
static bool prepare() {
  for (unsigned int i = 0; i < 5U; ++i)
    if (cudaMalloc(reinterpret_cast<void **>(&buffers[i]), TUC_BUFFER_BYTES[i]) != cudaSuccess)
      return false;
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
static bool evaluate(const float *a, const float *b, float *output, unsigned int *calls) {
  const float *host[2] = {a, b};
  unsigned int completed = 0U;
  for (unsigned int i = 0; i < 5U; ++i)
    if (cudaMemset(buffers[i], 0xff, TUC_BUFFER_BYTES[i]) != cudaSuccess) return false;
  for (unsigned int i = 0U; i < TUC_IO_COUNT; ++i) {
    const struct tuc_io_step s = io_step(i);
    if (s.phase != 1U) continue;
    if (cudaMemcpy(buffers[s.slot], host[s.slot], s.bytes, cudaMemcpyHostToDevice) != cudaSuccess ||
        cudaDeviceSynchronize() != cudaSuccess) return false;
    ++completed; ++io_completed; ++io_upload_calls; io_upload_bytes += s.bytes;
  }
  if (completed != 2U) return false;
  for (unsigned int i = 0; i < TUC_STEP_COUNT; ++i) {
    const struct tuc_step s = plan_step(i);
    unsigned int blocks = (TUC_BUFFER_BYTES[s.out] / 4U + 31U) / 32U;
#ifdef TUC_INCOMPLETE_COVERAGE
    if (s.opcode == 2U) blocks = 1U;
#endif
    switch (s.opcode) {
      case 1U: tuc_projection<<<blocks, 32>>>(buffers[s.a], buffers[s.b], buffers[s.out]); break;
      case 2U: tuc_relu<<<blocks, 32>>>(buffers[s.a], buffers[s.out]); break;
      case 3U: tuc_sum_axis1<<<blocks, 32>>>(buffers[s.a], buffers[s.out]); break;
      default: return false;
    }
    ++*calls;
    if (cudaGetLastError() != cudaSuccess || cudaDeviceSynchronize() != cudaSuccess) return false;
  }
  for (unsigned int i = 0U; i < TUC_IO_COUNT; ++i) {
    const struct tuc_io_step s = io_step(i);
    if (s.phase != 2U) continue;
#ifdef TUC_IO_SKIP_OUTPUT
    continue;
#endif
    if (cudaMemcpy(output, buffers[s.slot], s.bytes, cudaMemcpyDeviceToHost) != cudaSuccess ||
        cudaDeviceSynchronize() != cudaSuccess) return false;
    ++completed; ++io_completed; ++io_download_calls; io_download_bytes += s.bytes;
  }
  return completed == 3U;
}
#include "common.h"
