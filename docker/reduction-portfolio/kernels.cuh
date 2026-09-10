#ifndef TUC_REDUCTION_KERNELS_CUH
#define TUC_REDUCTION_KERNELS_CUH
__global__ void tuc_projection(const float *a, const float *b, float *projection) {
  const unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index < 8U) {
    const unsigned int row = index / 2U;
    const unsigned int column = index % 2U;
    float value = 0.0F;
    for (unsigned int inner = 0; inner < 8U; ++inner) {
      value += a[row * 8U + inner] * b[inner * 2U + column];
    }
    projection[index] = value;
  }
}

__global__ void tuc_sum_axis1(const float *projection, float *output) {
  const unsigned int row = blockIdx.x * blockDim.x + threadIdx.x;
  if (row < 4U) {
    float value = 0.0F;
    for (unsigned int column = 0; column < 2U; ++column) {
      value += projection[row * 2U + column];
    }
    output[row] = value;
  }
}
#endif
