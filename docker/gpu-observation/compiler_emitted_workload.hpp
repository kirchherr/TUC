#pragma once

#include <array>
#include <cstddef>

namespace tuc::compiler_emitted_gpu {

inline constexpr char kWorkloadContract[] =
    "research_triton_matmul_relu_4x8x2_f32.v0";
inline constexpr std::size_t kRows = 4;
inline constexpr std::size_t kInner = 8;
inline constexpr std::size_t kColumns = 2;
inline constexpr std::size_t kAElementCount = kRows * kInner;
inline constexpr std::size_t kBElementCount = kInner * kColumns;
inline constexpr std::size_t kOutputElementCount = kRows * kColumns;
inline constexpr std::array<float, 32> kA = {
    1.0F,
    -2.0F,
    0.5F,
    3.0F,
    0.0F,
    1.5F,
    -1.0F,
    2.0F,
    0.0F,
    1.0F,
    -1.0F,
    2.0F,
    3.0F,
    -0.5F,
    1.5F,
    -2.0F,
    2.0F,
    0.5F,
    1.0F,
    -1.5F,
    0.5F,
    2.5F,
    -3.0F,
    1.0F,
    -1.0F,
    2.0F,
    0.0F,
    1.0F,
    -2.0F,
    1.0F,
    0.5F,
    3.0F,
};
inline constexpr std::array<float, 16> kB = {
    1.0F,
    -1.0F,
    2.0F,
    0.5F,
    -1.0F,
    3.0F,
    0.5F,
    -2.0F,
    1.5F,
    1.0F,
    -0.5F,
    0.25F,
    2.5F,
    -1.5F,
    0.0F,
    2.0F,
};
inline constexpr std::array<float, 8> kExpectedOutput = {
    0.0F,
    0.0F,
    12.5F,
    0.0F,
    0.0F,
    11.875F,
    1.25F,
    3.5F,
};

}  // namespace tuc::compiler_emitted_gpu
