#include <cuda_runtime.h>
#include "inputs.h"
#include "kernels.cuh"
#define TUC_TARGET active->name
#define TUC_CODE_DIGEST TUC_MATRIX_CODE_DIGEST
#define TUC_WORKER "matrix"
#include "contract.h"
extern "C" {
void tuc_host_projection(const float *, const float *, float *);
void tuc_host_relu(const float *, float *);
void tuc_host_sum_axis1(const float *, float *);
}
#define host_projection tuc_host_projection
#define host_relu tuc_host_relu
#define host_sum tuc_host_sum_axis1
static bool target_ready(void) {
  if (!schedule_valid() || sizeof(float) != 4U) return false;
  if (active->mask == 0U) return true;
  int count = 0; cudaDeviceProp prop = {};
  return cudaGetDeviceCount(&count) == cudaSuccess && count == 1 &&
         cudaGetDeviceProperties(&prop, 0) == cudaSuccess && prop.major == 8 && prop.minor == 6 &&
         cudaSetDevice(0) == cudaSuccess;
}
static bool allocate_buffer(float **out, unsigned int bytes, unsigned int space) {
  if (space == 1U) return cudaMalloc(reinterpret_cast<void **>(out), bytes) == cudaSuccess;
  *out = static_cast<float *>(malloc(bytes)); return *out != NULL;
}
static bool release_buffer(float *p, unsigned int space) {
  if (space == 1U) return cudaFree(p) == cudaSuccess;
  free(p); return true;
}
static bool poison_buffer(float *p, unsigned int bytes, unsigned int space) {
  if (p == NULL) return false;
  if (space == 1U) return cudaMemset(p, 0xff, bytes) == cudaSuccess;
  for (unsigned int i = 0U; i < bytes / 4U; ++i) p[i] = NAN;
  return true;
}
static bool copy_buffer(float *out, const float *in, unsigned int bytes, unsigned int space) {
  return cudaMemcpy(out, in, bytes, space == 1U ? cudaMemcpyHostToDevice : cudaMemcpyDeviceToHost)
         == cudaSuccess && cudaDeviceSynchronize() == cudaSuccess;
}
static bool device_dispatch(unsigned int opcode, const float *a, const float *b, float *out) {
  unsigned int blocks = opcode == 3U ? 2U : 6U;
#ifdef TUC_INCOMPLETE_COVERAGE
  blocks = 1U;
#endif
  if (opcode == 1U) tuc_projection<<<blocks, 32>>>(a, b, out);
  else if (opcode == 2U) tuc_relu<<<blocks, 32>>>(a, out);
  else if (opcode == 3U) tuc_sum_axis1<<<blocks, 32>>>(a, out);
  else return false;
  return cudaGetLastError() == cudaSuccess && cudaDeviceSynchronize() == cudaSuccess;
}
#include "worker.h"
