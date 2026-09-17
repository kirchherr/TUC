#ifndef TUC_REDUCTION_KERNELS_CUH
#define TUC_REDUCTION_KERNELS_CUH
__global__ void tuc_projection(const float *a, const float *b, float *projection) {
  const unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index < 165U) {
    const unsigned int row = index / 5U;
    const unsigned int column = index % 5U;
    float value = 0.0F;
    for (unsigned int inner = 0; inner < 7U; ++inner) {
      value += a[row * 7U + inner] * b[inner * 5U + column];
    }
#ifdef TUC_MISSING_JOIN
    value = 0.0F;
#endif
    projection[index] = value;
  }
}

__global__ void tuc_sum_axis1(const float *projection, float *output) {
  const unsigned int row = blockIdx.x * blockDim.x + threadIdx.x;
  if (row < 33U) {
    float value = 0.0F;
    for (unsigned int column = 0; column < 5U; ++column) {
      value += projection[row * 5U + column];
    }
    output[row] = value;
  }
}

__global__ void tuc_relu_left(const float *input, float *output) {
  const unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index < 231U) {
#ifdef TUC_INCOMPLETE_LEFT
    if (index == 230U) return;
#endif
    const float value = input[index];
#if defined(TUC_BYPASS_LEFT) || defined(TUC_BYPASS_BOTH)
    output[index] = value;
#else
    output[index] = value < 0.0F ? 0.0F : value;
#endif
  }
}

__global__ void tuc_relu_right(const float *input, float *output) {
  const unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index < 35U) {
#ifdef TUC_INCOMPLETE_RIGHT
    if (index == 34U) return;
#endif
    const float value = input[index];
#if defined(TUC_BYPASS_RIGHT) || defined(TUC_BYPASS_BOTH)
    output[index] = value;
#else
    output[index] = value < 0.0F ? 0.0F : value;
#endif
  }
}
#endif
