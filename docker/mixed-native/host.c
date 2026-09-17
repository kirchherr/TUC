#include "generated.h"
#include "inputs.h"
#define TUC_TARGET "c11"
#define TUC_CODE_DIGEST TUC_C11_CODE_DIGEST
#define TUC_PLAN_HEADER "c11_plan.h"
#include "contract.h"
#define host_projection tuc_projection
#define host_relu tuc_relu
#define host_sum tuc_sum_axis1
static bool target_ready(void) { return schedule_valid() && sizeof(float) == 4U; }
static bool allocate_buffer(float **out, unsigned int bytes, unsigned int space) {
  if (space != 0U) return false;
  *out = malloc(bytes);
  return *out != NULL;
}
static bool release_buffer(float *p, unsigned int space) {
  if (space != 0U) return false;
  free(p); return true;
}
static bool poison_buffer(float *p, unsigned int bytes, unsigned int space) {
  if (space != 0U || p == NULL) return false;
  for (unsigned int i = 0U; i < bytes / 4U; ++i) p[i] = NAN;
  return true;
}
static bool copy_buffer(float *out, const float *in, unsigned int bytes, unsigned int space) {
  (void)out; (void)in; (void)bytes; (void)space; return false;
}
static bool device_dispatch(unsigned int opcode, const float *a, const float *b, float *out) {
  (void)opcode; (void)a; (void)b; (void)out; return false;
}
#include "worker.h"
