#ifndef TUC_REDUCTION_GENERATED_H
#define TUC_REDUCTION_GENERATED_H
void tuc_projection(const float *a, const float *b, float *projection);
void tuc_sum_axis1(const float *projection, float *output);
void tuc_relu_left(const float *input, float *output);
void tuc_relu_right(const float *input, float *output);
#endif
