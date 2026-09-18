#define _POSIX_C_SOURCE 200809L
#include "abi.h"
#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <unistd.h>

#define TUC_PLAN_FIELDS (6U + TUC_MAX_OPS + 3U * TUC_MAX_BUFFERS + 6U * TUC_MAX_EVENTS)
_Static_assert(sizeof(uint32_t) * CHAR_BIT == 32U, "contract probes require uint32_t");
_Static_assert(sizeof(struct tuc_buffer) == 3U * sizeof(uint32_t), "buffer ABI drift");
_Static_assert(sizeof(struct tuc_event) == 6U * sizeof(uint32_t), "event ABI drift");
_Static_assert(sizeof(struct tuc_plan) == TUC_PLAN_FIELDS * sizeof(uint32_t), "plan ABI drift");

/* Explicit field addresses avoid pointer arithmetic across structure members,
 * strict-aliasing assumptions, and accidental tests of padding bytes. */
static uint32_t plan_fields(struct tuc_plan *plan, uint32_t **fields) {
  uint32_t count = 0U;
  fields[count++] = &plan->graph;
  fields[count++] = &plan->profile;
  fields[count++] = &plan->buffer_count;
  fields[count++] = &plan->event_count;
  fields[count++] = &plan->buffer_bytes;
  fields[count++] = &plan->copy_bytes;
  for (uint32_t i = 0U; i < TUC_MAX_OPS; ++i) fields[count++] = &plan->targets[i];
  for (uint32_t i = 0U; i < TUC_MAX_BUFFERS; ++i) {
    fields[count++] = &plan->buffers[i].tensor;
    fields[count++] = &plan->buffers[i].space;
    fields[count++] = &plan->buffers[i].bytes;
  }
  for (uint32_t i = 0U; i < TUC_MAX_EVENTS; ++i) {
    fields[count++] = &plan->events[i].kind;
    fields[count++] = &plan->events[i].operation;
    fields[count++] = &plan->events[i].target;
    fields[count++] = &plan->events[i].input0;
    fields[count++] = &plan->events[i].input1;
    fields[count++] = &plan->events[i].output;
  }
  return count;
}

static bool graph_controls(const struct tuc_plan *plan) {
  struct tuc_graph changed = tuc_graphs[plan->graph];
  const struct tuc_graph *const baseline = &tuc_graphs[plan->graph];
  if (!tuc_validate_plan(&changed, plan, plan)) return false;
  changed.tensor_count = UINT32_MAX;
  if (tuc_validate_plan(&changed, plan, plan)) return false;
  changed = *baseline;
  changed.tensors[0].dim0 = UINT32_MAX;
  if (tuc_validate_plan(&changed, plan, plan)) return false;
  changed = *baseline;
  changed.operations[0].input0 = UINT32_MAX;
  if (tuc_validate_plan(&changed, plan, plan)) return false;
  changed = *baseline;
  changed.operations[0].output = changed.operations[0].input0;
  if (tuc_validate_plan(&changed, plan, plan)) return false;
  changed = *baseline;
  changed.operations[0].blocks ^= 1U;
  if (tuc_validate_plan(&changed, plan, plan)) return false;
  changed = *baseline;
  changed.input_ids[0] = changed.operations[0].output;
  if (tuc_validate_plan(&changed, plan, plan)) return false;
  changed = *baseline;
  changed.output_ids[0] = changed.input_ids[0];
  return !tuc_validate_plan(&changed, plan, plan);
}

int main(void) {
  (void)alarm(20U);
  uint32_t mutations = 0U;
  if (tuc_validate_plan(NULL, &tuc_plans[0], &tuc_plans[0]) ||
      tuc_validate_plan(&tuc_graphs[0], NULL, &tuc_plans[0]) ||
      tuc_validate_plan(&tuc_graphs[0], &tuc_plans[0], NULL)) return 1;
  for (uint32_t index = 0U; index < TUC_PLAN_COUNT; ++index) {
    const struct tuc_plan *const expected = &tuc_plans[index];
    if (expected->graph != index / 3U || expected->profile != index % 3U) return 1;
    const struct tuc_graph *const graph = &tuc_graphs[expected->graph];
    if (!tuc_validate_plan(graph, expected, expected) || !graph_controls(expected)) return 1;
    struct tuc_plan changed = *expected;
    uint32_t *fields[TUC_PLAN_FIELDS];
    const uint32_t count = plan_fields(&changed, fields);
    if (count != TUC_PLAN_FIELDS) return 1;
    for (uint32_t field = 0U; field < count; ++field) {
      for (uint32_t bit = 0U; bit < 32U; ++bit) {
        const uint32_t delta = UINT32_C(1) << bit;
        *fields[field] ^= delta;
        if (tuc_validate_plan(graph, &changed, expected)) return 1;
        *fields[field] ^= delta;
        ++mutations;
      }
    }
    if (!tuc_validate_plan(graph, &changed, expected)) return 1;
    /* The caller cannot admit changed artifacts by also relabeling expected. */
    changed.targets[TUC_MAX_OPS - 1U] ^= 1U;
    if (tuc_validate_plan(graph, &changed, &changed)) return 1;
  }
  if (mutations != (uint32_t)(sizeof(struct tuc_plan) / sizeof(uint32_t)) * 32U *
                   TUC_PLAN_COUNT) return 1;
  printf("{\"schema_version\":\"tuc.bounded_dag_native_contract.v0\","
         "\"status\":\"PASS\",\"plans\":%u,\"mutation_checks\":%" PRIu32 "}\n",
         TUC_PLAN_COUNT, mutations);
  return 0;
}
