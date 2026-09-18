#include "abi.h"
#include <cuda_runtime.h>
#include <stdlib.h>
#include <string.h>

#define TUC_WORKER "matrix"

static bool tuc_profile_supported(const struct tuc_plan *plan) {
  return plan->profile < 3U;
}

static bool tuc_target_ready(const struct tuc_plan *plan) {
  bool uses_device = false;
  const struct tuc_graph *graph = &tuc_graphs[plan->graph];
  for (uint32_t i = 0U; i < graph->op_count; ++i)
    uses_device = uses_device || plan->targets[i] == 1U;
  if (!uses_device) return true;
  int count = 0;
  cudaDeviceProp properties = {};
  return cudaGetDeviceCount(&count) == cudaSuccess && count == 1 &&
         cudaGetDeviceProperties(&properties, 0) == cudaSuccess &&
         properties.major == 8 && properties.minor == 6 &&
         cudaSetDevice(0) == cudaSuccess;
}

static bool tuc_allocate(float **out, uint32_t bytes, uint32_t space) {
  if (out == NULL || space > 1U) return false;
  *out = NULL;
  if (space == 1U)
    return cudaMalloc(reinterpret_cast<void **>(out), bytes) == cudaSuccess;
  *out = static_cast<float *>(malloc(bytes));
  return *out != NULL;
}

static bool tuc_release(float *pointer, uint32_t space) {
  if (space > 1U) return false;
  if (space == 1U) return cudaFree(pointer) == cudaSuccess;
  free(pointer);
  return true;
}

static bool tuc_poison(float *pointer, uint32_t bytes, uint32_t space) {
  if (pointer == NULL || space > 1U) return false;
  if (space == 1U)
    return cudaMemset(pointer, 0xff, bytes) == cudaSuccess &&
           cudaDeviceSynchronize() == cudaSuccess;
  const uint32_t poison = UINT32_C(0x7fc00001);
  for (uint32_t i = 0U; i < bytes / 4U; ++i)
    memcpy(pointer + i, &poison, sizeof(poison));
  return true;
}

static bool tuc_copy(float *out, const float *in, uint32_t bytes,
                     uint32_t destination, uint32_t source) {
  if (out == NULL || in == NULL || destination > 1U || source > 1U ||
      destination == source) return false;
  const cudaMemcpyKind kind = destination == 1U ? cudaMemcpyHostToDevice : cudaMemcpyDeviceToHost;
  return cudaMemcpy(out, in, bytes, kind) == cudaSuccess &&
         cudaDeviceSynchronize() == cudaSuccess;
}

static bool tuc_validation_read(float *out, const float *in, uint32_t bytes,
                                uint32_t space) {
  if (out == NULL || in == NULL || space > 1U) return false;
  if (space == 1U)
    return cudaMemcpy(out, in, bytes, cudaMemcpyDeviceToHost) == cudaSuccess &&
           cudaDeviceSynchronize() == cudaSuccess;
  memcpy(out, in, bytes);
  return true;
}

static bool tuc_dispatch(uint32_t space, uint32_t graph, uint32_t operation,
                          const float *a, const float *b, float *out) {
  if (space == 0U) return tuc_host_dispatch(graph, operation, a, b, out);
  return space == 1U && tuc_device_dispatch(graph, operation, a, b, out) &&
         cudaGetLastError() == cudaSuccess && cudaDeviceSynchronize() == cudaSuccess;
}

#include "worker.h"
