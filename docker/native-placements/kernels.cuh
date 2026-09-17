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

__global__ void tuc_relu(const float *projection, float *activated) {
  const unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index < 165U) {
    const float value = projection[index];
    activated[index] = value < 0.0F ? 0.0F : value;
  }
}
#endif
