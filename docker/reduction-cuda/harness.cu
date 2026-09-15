#include <cuda_runtime.h>
#include "kernels.cuh"
#include "inputs.h"
#include "cuda_digest.h"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <unistd.h>

namespace {
bool security_ok() {
  if (getuid() != 10001U || getgid() != 10001U) return false;
  FILE *status = std::fopen("/proc/self/status", "r");
  if (status == nullptr) return false;
  bool caps = false, privileges = false, seccomp = false;
  char line[256] = {};
  unsigned int count = 0;
  while (count++ < 1024U && std::fgets(line, sizeof(line), status) != nullptr) {
    char value[32] = {};
    int flag = -1;
    if (std::sscanf(line, "CapEff:%31s", value) == 1)
      caps = std::strcmp(value, "0000000000000000") == 0;
    else if (std::sscanf(line, "NoNewPrivs:%d", &flag) == 1) privileges = flag == 1;
    else if (std::sscanf(line, "Seccomp:%d", &flag) == 1) seccomp = flag == 2;
  }
  const bool closed = std::fclose(status) == 0;
  return closed && count < 1024U && caps && privileges && seccomp;
}

bool reference_matches(const float *output) {
  // Contract B first in binary64, independently of the generated kernels.
  constexpr double expected[4] = {-5.875, 2.625, 5.125, 4.75};
  for (unsigned int row = 0; row < 4U; ++row) {
    double reference = 0.0;
    for (unsigned int k = 0; k < 8U; ++k)
      reference += static_cast<double>(TUC_A[row * 8U + k]) *
                   (static_cast<double>(TUC_B[k * 2U]) + TUC_B[k * 2U + 1U]);
    if (!std::isfinite(output[row]) || reference != expected[row] ||
        static_cast<double>(output[row]) != expected[row]) return false;
  }
  return true;
}

int emit(const char *mode, bool passed, bool security, int visible,
         unsigned int calls, unsigned int bytes, bool correct, const char *reason) {
  std::printf("{\"schema_version\":\"tuc.bounded_reduction_cuda_observation.v0\","
      "\"status\":\"%s\",\"mode\":\"%s\",\"reason_code\":\"%s\","
      "\"source_intent_digest\":\"%s\",\"generated_source_digest\":\"%s\","
      "\"c11_source_digest\":\"%s\",\"vector_digest\":\"%s\","
      "\"target\":\"nvidia_cuda_sm86\",\"visible_device_count\":%d,"
      "\"generated_function_calls\":%u,\"working_set_bytes\":%u,"
      "\"reference_correctness\":%s,\"security_boundary_passed\":%s,"
      "\"output_shape\":[4],\"raw_values_serialized\":false}\n",
      passed ? "PASS" : "ERROR", mode, reason, TUC_SOURCE_INTENT_DIGEST,
      TUC_CUDA_KERNEL_DIGEST, TUC_GENERATED_SOURCE_DIGEST, TUC_VECTOR_DIGEST,
      visible, calls, bytes, correct ? "true" : "false", security ? "true" : "false");
  return passed ? 0 : 1;
}

bool release(float **buffers) {
  bool ok = true;
  for (unsigned int i = 0; i < 4U; ++i) {
    if (buffers[i] != nullptr) ok = (cudaFree(buffers[i]) == cudaSuccess) && ok;
    buffers[i] = nullptr;
  }
  return ok;
}
}  // namespace

int main(int argc, char **argv) {
  alarm(15U);
  const bool execute = argc == 2 && std::strcmp(argv[1], "--execute") == 0;
  const bool preflight = argc == 2 && std::strcmp(argv[1], "--preflight") == 0;
  const char *mode = execute ? "execute" : "preflight";
  if (!execute && !preflight) return emit("invalid", false, false, 0, 0, 0, false, "invalid_invocation");
  if (!security_ok()) return emit(mode, false, false, 0, 0, 0, false, "security_boundary_mismatch");
  int count = 0;
  cudaDeviceProp prop = {};
  if (cudaGetDeviceCount(&count) != cudaSuccess || count != 1 ||
      cudaGetDeviceProperties(&prop, 0) != cudaSuccess || prop.major != 8 || prop.minor != 6 ||
      cudaSetDevice(0) != cudaSuccess)
    return emit(mode, false, true, count, 0, 0, false, "device_boundary_mismatch");
  if (preflight) return emit(mode, true, true, 1, 0, 0, false, "none");

  static_assert(sizeof(float) == 4U);
  constexpr unsigned int sizes[4] = {128U, 64U, 32U, 16U};
  float *buffers[4] = {};
  unsigned int bytes = 0, calls = 0;
  const char *reason = "none";
  for (unsigned int i = 0; i < 4U; ++i) {
    if (cudaMalloc(reinterpret_cast<void **>(&buffers[i]), sizes[i]) != cudaSuccess) {
      reason = "allocation_failed";
      break;
    }
    bytes += sizes[i];
  }
  float output[4] = {};
  if (std::strcmp(reason, "none") == 0) {
    if (cudaMemcpy(buffers[0], TUC_A, sizes[0], cudaMemcpyHostToDevice) != cudaSuccess ||
        cudaMemcpy(buffers[1], TUC_B, sizes[1], cudaMemcpyHostToDevice) != cudaSuccess ||
        cudaMemset(buffers[2], 0, sizes[2]) != cudaSuccess ||
        cudaMemset(buffers[3], 0, sizes[3]) != cudaSuccess) reason = "input_transfer_failed";
  }
  if (std::strcmp(reason, "none") == 0) {
    tuc_projection<<<1, 32>>>(buffers[0], buffers[1], buffers[2]);
    ++calls;
    if (cudaGetLastError() != cudaSuccess || cudaDeviceSynchronize() != cudaSuccess)
      reason = "matmul_failed";
  }
  if (std::strcmp(reason, "none") == 0) {
    tuc_sum_axis1<<<1, 32>>>(buffers[2], buffers[3]);
    ++calls;
    if (cudaGetLastError() != cudaSuccess || cudaDeviceSynchronize() != cudaSuccess)
      reason = "reduction_failed";
  }
  if (std::strcmp(reason, "none") == 0) {
    if (cudaMemcpy(output, buffers[3], sizes[3], cudaMemcpyDeviceToHost) != cudaSuccess)
      reason = "output_transfer_failed";
    else if (!reference_matches(output)) reason = "reference_mismatch";
  }
  if (!release(buffers)) reason = "cleanup_failed";
  const bool passed = std::strcmp(reason, "none") == 0;
  return emit(mode, passed, true, 1, calls, bytes, passed, reason);
}
