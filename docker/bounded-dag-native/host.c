#include "abi.h"
#include <stdlib.h>
#include <string.h>

#define TUC_WORKER "c11"

static bool tuc_profile_supported(const struct tuc_plan *plan) {
  return plan->profile == 0U;
}

static bool tuc_target_ready(const struct tuc_plan *plan) {
  (void)plan;
  return true;
}

static bool tuc_allocate(float **out, uint32_t bytes, uint32_t space) {
  if (space != 0U || out == NULL) return false;
  *out = (float *)malloc(bytes);
  return *out != NULL;
}

static bool tuc_release(float *pointer, uint32_t space) {
  if (space != 0U) return false;
  free(pointer);
  return true;
}

static bool tuc_poison(float *pointer, uint32_t bytes, uint32_t space) {
  if (space != 0U || pointer == NULL) return false;
  const uint32_t poison = UINT32_C(0x7fc00001);
  for (uint32_t i = 0U; i < bytes / 4U; ++i)
    memcpy(pointer + i, &poison, sizeof(poison));
  return true;
}

static bool tuc_copy(float *out, const float *in, uint32_t bytes,
                     uint32_t destination, uint32_t source) {
  (void)out; (void)in; (void)bytes; (void)destination; (void)source;
  return false;
}

static bool tuc_validation_read(float *out, const float *in, uint32_t bytes,
                                uint32_t space) {
  if (space != 0U || out == NULL || in == NULL) return false;
  memcpy(out, in, bytes);
  return true;
}

static bool tuc_dispatch(uint32_t space, uint32_t graph, uint32_t operation,
                          const float *a, const float *b, float *out) {
  return space == 0U && tuc_host_dispatch(graph, operation, a, b, out);
}

#include "worker.h"
