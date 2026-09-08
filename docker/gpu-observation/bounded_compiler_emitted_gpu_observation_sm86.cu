#include "compiler_emitted_workload.hpp"
#include "generated_compiler_emitted_sm86_kernels.cuh"

#include <cuda_runtime.h>

#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <sys/types.h>
#include <unistd.h>

#ifndef TUC_GPU_OBSERVATION_WORKLOAD_DIGEST
#error "TUC_GPU_OBSERVATION_WORKLOAD_DIGEST must be supplied by the reviewed build"
#endif

namespace {

constexpr int kExpectedUid = 10001;
constexpr int kExpectedGid = 10001;
constexpr int kExpectedComputeMajor = 8;
constexpr int kExpectedComputeMinor = 6;
constexpr float kTolerance = 1.0e-5F;
constexpr std::size_t kWorkloadAllocationBytes =
    (tuc::compiler_emitted_gpu::kAElementCount +
     tuc::compiler_emitted_gpu::kBElementCount +
     (2 * tuc::compiler_emitted_gpu::kOutputElementCount)) *
    sizeof(float);
static_assert(kWorkloadAllocationBytes == 256);

struct SecurityObservation {
  bool status_read = false;
  bool effective_capabilities_zero = false;
  int no_new_privileges = -1;
  int seccomp_mode = -1;
};

SecurityObservation read_security_observation() {
  SecurityObservation observation;
  std::FILE* status = std::fopen("/proc/self/status", "r");
  if (status == nullptr) {
    return observation;
  }

  char line[256] = {};
  char capability_value[32] = {};
  bool capability_seen = false;
  bool no_new_privileges_seen = false;
  bool seccomp_seen = false;
  std::size_t line_count = 0;
  while (line_count < 1024 && std::fgets(line, sizeof(line), status) != nullptr) {
    ++line_count;
    if (std::sscanf(line, "CapEff:%31s", capability_value) == 1) {
      capability_seen = true;
      observation.effective_capabilities_zero =
          std::strcmp(capability_value, "0000000000000000") == 0;
    } else if (std::sscanf(line, "NoNewPrivs:%d", &observation.no_new_privileges) ==
               1) {
      no_new_privileges_seen = true;
    } else if (std::sscanf(line, "Seccomp:%d", &observation.seccomp_mode) == 1) {
      seccomp_seen = true;
    }
  }
  const bool closed = std::fclose(status) == 0;
  observation.status_read = closed && capability_seen && no_new_privileges_seen &&
                            seccomp_seen && line_count < 1024;
  return observation;
}

bool security_boundary_passed(const SecurityObservation& observation) {
  return observation.status_read && observation.effective_capabilities_zero &&
         observation.no_new_privileges == 1 && observation.seccomp_mode == 2 &&
         static_cast<int>(::getuid()) == kExpectedUid &&
         static_cast<int>(::getgid()) == kExpectedGid;
}

void emit_observation(const char* mode, const char* status, const char* reason_code,
                      const char* accelerator_class, int visible_device_count,
                      int kernel_launch_count, std::size_t allocation_bytes,
                      const char* reference_check_status,
                      const SecurityObservation& security) {
  std::printf(
      "{\"accelerator_class\":\"%s\","
      "\"device_name_serialized\":false,"
      "\"driver_version_serialized\":false,"
      "\"dtype\":\"float32\","
      "\"environment_serialized\":false,"
      "\"hardware_identifiers_serialized\":false,"
      "\"kernel_launch_count\":%d,"
      "\"mode\":\"%s\","
      "\"operation_families\":[\"matmul\",\"elementwise\"],"
      "\"protocol\":\"tuc.bounded_compiler_emitted_gpu_observation_worker.v0\","
      "\"raw_tensor_values_serialized\":false,"
      "\"raw_timing_samples_serialized\":false,"
      "\"reason_code\":\"%s\","
      "\"reference_check_status\":\"%s\","
      "\"security\":{"
      "\"effective_capabilities_zero\":%s,"
      "\"gid\":%d,"
      "\"no_new_privileges\":%d,"
      "\"seccomp_mode\":%d,"
      "\"status_read\":%s,"
      "\"uid\":%d},"
      "\"status\":\"%s\","
      "\"tensor_shape\":[4,2],"
      "\"visible_device_count\":%d,"
      "\"workload_allocation_bytes\":%zu,"
      "\"workload_contract\":\"%s\","
      "\"workload_manifest_digest\":\"%s\"}\n",
      accelerator_class, kernel_launch_count, mode, reason_code,
      reference_check_status,
      security.effective_capabilities_zero ? "true" : "false",
      static_cast<int>(::getgid()), security.no_new_privileges,
      security.seccomp_mode, security.status_read ? "true" : "false",
      static_cast<int>(::getuid()), status, visible_device_count, allocation_bytes,
      tuc::compiler_emitted_gpu::kWorkloadContract,
      TUC_GPU_OBSERVATION_WORKLOAD_DIGEST);
  std::fflush(stdout);
}

bool cpu_reference_matches_manifest() {
  std::array<float, tuc::compiler_emitted_gpu::kOutputElementCount> reference = {};
  for (std::size_t row = 0; row < tuc::compiler_emitted_gpu::kRows; ++row) {
    for (std::size_t column = 0; column < tuc::compiler_emitted_gpu::kColumns;
         ++column) {
      float value = 0.0F;
      for (std::size_t inner = 0; inner < tuc::compiler_emitted_gpu::kInner;
           ++inner) {
        value += tuc::compiler_emitted_gpu::kA[
                     row * tuc::compiler_emitted_gpu::kInner + inner] *
                 tuc::compiler_emitted_gpu::kB[
                     inner * tuc::compiler_emitted_gpu::kColumns + column];
      }
      const std::size_t index =
          row * tuc::compiler_emitted_gpu::kColumns + column;
      reference[index] = value > 0.0F ? value : 0.0F;
    }
  }
  for (std::size_t index = 0; index < reference.size(); ++index) {
    if (std::fabs(reference[index] -
                  tuc::compiler_emitted_gpu::kExpectedOutput[index]) > kTolerance) {
      return false;
    }
  }
  return true;
}

bool output_matches_reference(
    const std::array<float, tuc::compiler_emitted_gpu::kOutputElementCount>& output) {
  for (std::size_t index = 0; index < output.size(); ++index) {
    if (!std::isfinite(output[index]) ||
        std::fabs(output[index] -
                  tuc::compiler_emitted_gpu::kExpectedOutput[index]) > kTolerance) {
      return false;
    }
  }
  return true;
}

bool release_device_memory(float*& a, float*& b, float*& projection,
                           float*& activated) {
  bool released = true;
  if (activated != nullptr) {
    released = cudaFree(activated) == cudaSuccess && released;
    activated = nullptr;
  }
  if (projection != nullptr) {
    released = cudaFree(projection) == cudaSuccess && released;
    projection = nullptr;
  }
  if (b != nullptr) {
    released = cudaFree(b) == cudaSuccess && released;
    b = nullptr;
  }
  if (a != nullptr) {
    released = cudaFree(a) == cudaSuccess && released;
    a = nullptr;
  }
  return released;
}

int fail(const char* mode, const char* reason_code,
         const SecurityObservation& security, float*& a, float*& b,
         float*& projection, float*& activated) {
  static_cast<void>(release_device_memory(a, b, projection, activated));
  emit_observation(mode, "ERROR", reason_code, "not_accepted", 0, 0, 0,
                   "not_executed", security);
  return 1;
}

}  // namespace

int main(int argc, char** argv) {
  const bool preflight = argc == 2 && std::strcmp(argv[1], "--preflight") == 0;
  const bool execute = argc == 2 && std::strcmp(argv[1], "--execute") == 0;
  const char* mode = execute ? "execute" : "preflight";
  SecurityObservation security = read_security_observation();
  float* device_a = nullptr;
  float* device_b = nullptr;
  float* device_projection = nullptr;
  float* device_activated = nullptr;

  if (!preflight && !execute) {
    return fail("invalid", "invalid_invocation", security, device_a, device_b,
                device_projection, device_activated);
  }
  if (!security_boundary_passed(security)) {
    return fail(mode, "security_boundary_mismatch", security, device_a, device_b,
                device_projection, device_activated);
  }
  if (!cpu_reference_matches_manifest()) {
    return fail(mode, "workload_reference_mismatch", security, device_a, device_b,
                device_projection, device_activated);
  }

  int device_count = 0;
  if (cudaGetDeviceCount(&device_count) != cudaSuccess) {
    return fail(mode, "device_query_failed", security, device_a, device_b,
                device_projection, device_activated);
  }
  if (device_count != 1) {
    return fail(mode, "device_visibility_mismatch", security, device_a, device_b,
                device_projection, device_activated);
  }

  cudaDeviceProp properties = {};
  if (cudaGetDeviceProperties(&properties, 0) != cudaSuccess) {
    return fail(mode, "device_properties_failed", security, device_a, device_b,
                device_projection, device_activated);
  }
  if (properties.major != kExpectedComputeMajor ||
      properties.minor != kExpectedComputeMinor) {
    return fail(mode, "accelerator_class_mismatch", security, device_a, device_b,
                device_projection, device_activated);
  }
  if (cudaSetDevice(0) != cudaSuccess) {
    return fail(mode, "device_selection_failed", security, device_a, device_b,
                device_projection, device_activated);
  }

  if (preflight) {
    emit_observation(mode, "PASS", "none", "nvidia_cuda_sm86", 1, 0, 0,
                     "not_executed", security);
    return 0;
  }

  constexpr std::size_t a_bytes =
      tuc::compiler_emitted_gpu::kAElementCount * sizeof(float);
  constexpr std::size_t b_bytes =
      tuc::compiler_emitted_gpu::kBElementCount * sizeof(float);
  constexpr std::size_t output_bytes =
      tuc::compiler_emitted_gpu::kOutputElementCount * sizeof(float);
  if (cudaMalloc(reinterpret_cast<void**>(&device_a), a_bytes) != cudaSuccess ||
      cudaMalloc(reinterpret_cast<void**>(&device_b), b_bytes) != cudaSuccess ||
      cudaMalloc(reinterpret_cast<void**>(&device_projection), output_bytes) !=
          cudaSuccess ||
      cudaMalloc(reinterpret_cast<void**>(&device_activated), output_bytes) !=
          cudaSuccess) {
    return fail(mode, "bounded_allocation_failed", security, device_a, device_b,
                device_projection, device_activated);
  }
  if (cudaMemcpy(device_a, tuc::compiler_emitted_gpu::kA.data(), a_bytes,
                 cudaMemcpyHostToDevice) != cudaSuccess ||
      cudaMemcpy(device_b, tuc::compiler_emitted_gpu::kB.data(), b_bytes,
                 cudaMemcpyHostToDevice) != cudaSuccess) {
    return fail(mode, "input_transfer_failed", security, device_a, device_b,
                device_projection, device_activated);
  }

  tuc::compiler_emitted_gpu::tuc_projection_matmul_4x8x2_f32
      <<<1, tuc::compiler_emitted_gpu::kThreadsPerBlock>>>(
          device_a, device_b, device_projection);
  if (cudaPeekAtLastError() != cudaSuccess) {
    return fail(mode, "matmul_launch_failed", security, device_a, device_b,
                device_projection, device_activated);
  }
  tuc::compiler_emitted_gpu::tuc_activated_relu_4x2_f32
      <<<1, tuc::compiler_emitted_gpu::kThreadsPerBlock>>>(device_projection,
                                                           device_activated);
  if (cudaPeekAtLastError() != cudaSuccess ||
      cudaDeviceSynchronize() != cudaSuccess) {
    return fail(mode, "kernel_completion_failed", security, device_a, device_b,
                device_projection, device_activated);
  }

  std::array<float, tuc::compiler_emitted_gpu::kOutputElementCount> output = {};
  if (cudaMemcpy(output.data(), device_activated, output_bytes,
                 cudaMemcpyDeviceToHost) != cudaSuccess) {
    return fail(mode, "output_transfer_failed", security, device_a, device_b,
                device_projection, device_activated);
  }
  if (!output_matches_reference(output)) {
    return fail(mode, "reference_mismatch", security, device_a, device_b,
                device_projection, device_activated);
  }

  if (!release_device_memory(device_a, device_b, device_projection,
                             device_activated)) {
    return fail(mode, "device_cleanup_failed", security, device_a, device_b,
                device_projection, device_activated);
  }
  emit_observation(mode, "PASS", "none", "nvidia_cuda_sm86", 1, 2,
                   kWorkloadAllocationBytes, "passed", security);
  return 0;
}
