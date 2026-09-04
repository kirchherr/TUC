#include "objective_delta_workload.hpp"

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

constexpr int kThreadsPerBlock = 32;
constexpr int kExpectedUid = 10001;
constexpr int kExpectedGid = 10001;
constexpr int kExpectedComputeMajor = 7;
constexpr int kExpectedComputeMinor = 0;
constexpr double kTolerance = 1.0e-12;
constexpr std::size_t kWorkloadAllocationBytes =
    4 * tuc::gpu_observation::kElementCount * sizeof(double);

struct SecurityObservation {
  bool status_read = false;
  bool effective_capabilities_zero = false;
  int no_new_privileges = -1;
  int seccomp_mode = -1;
};

__global__ void fixed_matmul_kernel(const double* lhs, const double* rhs,
                                    double* projection) {
  const int index = static_cast<int>(threadIdx.x);
  if (index >= static_cast<int>(tuc::gpu_observation::kElementCount)) {
    return;
  }
  const int row = index / static_cast<int>(tuc::gpu_observation::kDimension);
  const int column = index % static_cast<int>(tuc::gpu_observation::kDimension);
  double value = 0.0;
  for (int inner = 0;
       inner < static_cast<int>(tuc::gpu_observation::kDimension); ++inner) {
    value += lhs[row * static_cast<int>(tuc::gpu_observation::kDimension) + inner] *
             rhs[inner * static_cast<int>(tuc::gpu_observation::kDimension) +
                 column];
  }
  projection[index] = value;
}

__global__ void fixed_elementwise_kernel(const double* projection,
                                         double* activated) {
  const int index = static_cast<int>(threadIdx.x);
  if (index >= static_cast<int>(tuc::gpu_observation::kElementCount)) {
    return;
  }
  activated[index] = projection[index];
}

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
      "\"dtype\":\"float64\","
      "\"environment_serialized\":false,"
      "\"hardware_identifiers_serialized\":false,"
      "\"kernel_launch_count\":%d,"
      "\"mode\":\"%s\","
      "\"operation_families\":[\"matmul\",\"elementwise\"],"
      "\"protocol\":\"tuc.bounded_gpu_observation_worker.v0\","
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
      "\"tensor_shape\":[2,2],"
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
      tuc::gpu_observation::kWorkloadContract,
      TUC_GPU_OBSERVATION_WORKLOAD_DIGEST);
  std::fflush(stdout);
}

bool cpu_reference_matches_manifest() {
  std::array<double, tuc::gpu_observation::kElementCount> reference = {};
  for (std::size_t row = 0; row < tuc::gpu_observation::kDimension; ++row) {
    for (std::size_t column = 0; column < tuc::gpu_observation::kDimension;
         ++column) {
      double value = 0.0;
      for (std::size_t inner = 0; inner < tuc::gpu_observation::kDimension;
           ++inner) {
        value += tuc::gpu_observation::kLhs[
                     row * tuc::gpu_observation::kDimension + inner] *
                 tuc::gpu_observation::kRhs[
                     inner * tuc::gpu_observation::kDimension + column];
      }
      reference[row * tuc::gpu_observation::kDimension + column] = value;
    }
  }
  for (std::size_t index = 0; index < reference.size(); ++index) {
    if (std::fabs(reference[index] -
                  tuc::gpu_observation::kExpectedOutput[index]) > kTolerance) {
      return false;
    }
  }
  return true;
}

bool output_matches_reference(
    const std::array<double, tuc::gpu_observation::kElementCount>& output) {
  for (std::size_t index = 0; index < output.size(); ++index) {
    if (!std::isfinite(output[index]) ||
        std::fabs(output[index] - tuc::gpu_observation::kExpectedOutput[index]) >
            kTolerance) {
      return false;
    }
  }
  return true;
}

bool release_device_memory(double*& lhs, double*& rhs, double*& projection,
                           double*& activated) {
  bool released = true;
  if (activated != nullptr) {
    released = cudaFree(activated) == cudaSuccess && released;
    activated = nullptr;
  }
  if (projection != nullptr) {
    released = cudaFree(projection) == cudaSuccess && released;
    projection = nullptr;
  }
  if (rhs != nullptr) {
    released = cudaFree(rhs) == cudaSuccess && released;
    rhs = nullptr;
  }
  if (lhs != nullptr) {
    released = cudaFree(lhs) == cudaSuccess && released;
    lhs = nullptr;
  }
  return released;
}

int fail(const char* mode, const char* reason_code,
         const SecurityObservation& security, double*& lhs, double*& rhs,
         double*& projection, double*& activated) {
  static_cast<void>(release_device_memory(lhs, rhs, projection, activated));
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
  double* device_lhs = nullptr;
  double* device_rhs = nullptr;
  double* device_projection = nullptr;
  double* device_activated = nullptr;

  if (!preflight && !execute) {
    return fail("invalid", "invalid_invocation", security, device_lhs, device_rhs,
                device_projection, device_activated);
  }
  if (!security_boundary_passed(security)) {
    return fail(mode, "security_boundary_mismatch", security, device_lhs,
                device_rhs, device_projection, device_activated);
  }
  if (!cpu_reference_matches_manifest()) {
    return fail(mode, "workload_reference_mismatch", security, device_lhs,
                device_rhs, device_projection, device_activated);
  }

  int device_count = 0;
  if (cudaGetDeviceCount(&device_count) != cudaSuccess) {
    return fail(mode, "device_query_failed", security, device_lhs, device_rhs,
                device_projection, device_activated);
  }
  if (device_count != 1) {
    return fail(mode, "device_visibility_mismatch", security, device_lhs,
                device_rhs, device_projection, device_activated);
  }

  cudaDeviceProp properties = {};
  if (cudaGetDeviceProperties(&properties, 0) != cudaSuccess) {
    return fail(mode, "device_properties_failed", security, device_lhs,
                device_rhs, device_projection, device_activated);
  }
  if (properties.major != kExpectedComputeMajor ||
      properties.minor != kExpectedComputeMinor) {
    return fail(mode, "accelerator_class_mismatch", security, device_lhs,
                device_rhs, device_projection, device_activated);
  }
  if (cudaSetDevice(0) != cudaSuccess) {
    return fail(mode, "device_selection_failed", security, device_lhs,
                device_rhs, device_projection, device_activated);
  }

  if (preflight) {
    emit_observation(mode, "PASS", "none", "nvidia_cuda_sm70", 1, 0, 0,
                     "not_executed", security);
    return 0;
  }

  constexpr std::size_t bytes =
      tuc::gpu_observation::kElementCount * sizeof(double);
  if (cudaMalloc(reinterpret_cast<void**>(&device_lhs), bytes) != cudaSuccess ||
      cudaMalloc(reinterpret_cast<void**>(&device_rhs), bytes) != cudaSuccess ||
      cudaMalloc(reinterpret_cast<void**>(&device_projection), bytes) !=
          cudaSuccess ||
      cudaMalloc(reinterpret_cast<void**>(&device_activated), bytes) !=
          cudaSuccess) {
    return fail(mode, "bounded_allocation_failed", security, device_lhs,
                device_rhs, device_projection, device_activated);
  }
  if (cudaMemcpy(device_lhs, tuc::gpu_observation::kLhs.data(), bytes,
                 cudaMemcpyHostToDevice) != cudaSuccess ||
      cudaMemcpy(device_rhs, tuc::gpu_observation::kRhs.data(), bytes,
                 cudaMemcpyHostToDevice) != cudaSuccess) {
    return fail(mode, "input_transfer_failed", security, device_lhs, device_rhs,
                device_projection, device_activated);
  }

  fixed_matmul_kernel<<<1, kThreadsPerBlock>>>(device_lhs, device_rhs,
                                               device_projection);
  if (cudaPeekAtLastError() != cudaSuccess) {
    return fail(mode, "matmul_launch_failed", security, device_lhs, device_rhs,
                device_projection, device_activated);
  }
  fixed_elementwise_kernel<<<1, kThreadsPerBlock>>>(device_projection,
                                                    device_activated);
  if (cudaPeekAtLastError() != cudaSuccess ||
      cudaDeviceSynchronize() != cudaSuccess) {
    return fail(mode, "kernel_completion_failed", security, device_lhs,
                device_rhs, device_projection, device_activated);
  }

  std::array<double, tuc::gpu_observation::kElementCount> output = {};
  if (cudaMemcpy(output.data(), device_activated, bytes, cudaMemcpyDeviceToHost) !=
      cudaSuccess) {
    return fail(mode, "output_transfer_failed", security, device_lhs, device_rhs,
                device_projection, device_activated);
  }
  if (!output_matches_reference(output)) {
    return fail(mode, "reference_mismatch", security, device_lhs, device_rhs,
                device_projection, device_activated);
  }

  if (!release_device_memory(device_lhs, device_rhs, device_projection,
                             device_activated)) {
    return fail(mode, "device_cleanup_failed", security, device_lhs, device_rhs,
                device_projection, device_activated);
  }
  emit_observation(mode, "PASS", "none", "nvidia_cuda_sm70", 1, 2,
                   kWorkloadAllocationBytes, "passed", security);
  return 0;
}
