#ifndef TUC_COMPILER_EMITTED_C11_WORKLOAD_H
#define TUC_COMPILER_EMITTED_C11_WORKLOAD_H

#define TUC_C11_WORKLOAD_CONTRACT "research_triton_matmul_relu_4x8x2_f32.v0"
#define TUC_C11_ROWS 4U
#define TUC_C11_INNER 8U
#define TUC_C11_COLUMNS 2U
#define TUC_C11_A_COUNT 32U
#define TUC_C11_B_COUNT 16U
#define TUC_C11_OUTPUT_COUNT 8U

static const float TUC_C11_A[32] = {
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
static const float TUC_C11_B[16] = {
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
static const float TUC_C11_EXPECTED_OUTPUT[8] = {
    0.0F,
    0.0F,
    12.5F,
    0.0F,
    0.0F,
    11.875F,
    1.25F,
    3.5F,
};

#endif
