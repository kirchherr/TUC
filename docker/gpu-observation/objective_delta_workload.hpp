#pragma once

#include <array>
#include <cstddef>

namespace tuc::gpu_observation {

inline constexpr char kWorkloadContract[] =
    "objective_delta_matmul_elementwise_2x2_f64.v0";
inline constexpr std::size_t kDimension = 2;
inline constexpr std::size_t kElementCount = 4;
inline constexpr std::array<double, kElementCount> kLhs = {
    1.0,
    -2.0,
    0.5,
    3.0,
};
inline constexpr std::array<double, kElementCount> kRhs = {
    2.0,
    1.0,
    -1.0,
    0.25,
};
inline constexpr std::array<double, kElementCount> kExpectedOutput = {
    4.0,
    0.5,
    -2.0,
    1.25,
};

}  // namespace tuc::gpu_observation
