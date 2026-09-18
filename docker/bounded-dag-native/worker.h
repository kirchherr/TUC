#ifndef TUC_DAG_NATIVE_WORKER_H
#define TUC_DAG_NATIVE_WORKER_H
#include "abi.h"
#include <fenv.h>
#include <float.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <xmmintrin.h>

#ifndef TUC_FAULT
#define TUC_FAULT 0
#endif
#if TUC_FAULT < 0 || TUC_FAULT > 4
#error "unsupported bounded DAG fault"
#endif

struct tuc_storage {
  float *slots[TUC_MAX_BUFFERS];
  bool owned[TUC_MAX_BUFFERS];
};

static bool tuc_selector(const char *text, uint32_t *index) {
  if (text == NULL || text[0] < '0' || text[0] > '9') return false;
  uint32_t value = (uint32_t)(text[0] - '0');
  if (text[1] != '\0') {
    if (text[0] == '0' || text[1] < '0' || text[1] > '9' || text[2] != '\0') return false;
    value = 10U * value + (uint32_t)(text[1] - '0');
  }
  if (value >= TUC_PLAN_COUNT) return false;
  *index = value;
  return true;
}

static bool tuc_security_ok(void) {
  if (getuid() != 10001U || geteuid() != 10001U ||
      getgid() != 10001U || getegid() != 10001U) return false;
  FILE *status = fopen("/proc/self/status", "r");
  if (status == NULL) return false;
  bool caps = false, privileges = false, seccomp = false;
  char line[256] = {0};
  uint32_t count = 0U;
  while (count++ < 1024U && fgets(line, sizeof(line), status) != NULL) {
    char value[32] = {0};
    int flag = -1;
    if (sscanf(line, "CapEff:%31s", value) == 1)
      caps = strcmp(value, "0000000000000000") == 0;
    else if (sscanf(line, "NoNewPrivs:%d", &flag) == 1) privileges = flag == 1;
    else if (sscanf(line, "Seccomp:%d", &flag) == 1) seccomp = flag == 2;
  }
  const bool read_ok = ferror(status) == 0;
  const bool closed = fclose(status) == 0;
  return closed && read_ok && count < 1024U && caps && privileges && seccomp;
}

static bool tuc_float_environment(void) {
  /* DAZ, FTZ and both SSE rounding-control bits must remain disabled. */
  const unsigned int forbidden = 0x8040U | 0x6000U;
  return sizeof(float) == 4U && sizeof(uint32_t) == 4U &&
         FLT_RADIX == 2 && FLT_MANT_DIG == 24 && FLT_MAX_EXP == 128 &&
         FLT_MIN_EXP == -125 && FLT_EVAL_METHOD == 0 &&
         fegetround() == FE_TONEAREST && (_mm_getcsr() & forbidden) == 0U;
}

static bool tuc_normal_bits(uint32_t bits) {
  const uint32_t magnitude = bits & UINT32_C(0x7fffffff);
  const uint32_t exponent = magnitude & UINT32_C(0x7f800000);
  return magnitude == 0U || (exponent != 0U && exponent != UINT32_C(0x7f800000));
}

static bool tuc_is_input(const struct tuc_graph *graph, uint32_t tensor) {
  for (uint32_t i = 0U; i < graph->input_count; ++i)
    if (graph->input_ids[i] == tensor) return true;
  return false;
}

static bool tuc_is_output(const struct tuc_graph *graph, uint32_t tensor) {
  for (uint32_t i = 0U; i < graph->output_count; ++i)
    if (graph->output_ids[i] == tensor) return true;
  return false;
}

static bool tuc_corpus_valid(const struct tuc_graph *graph, const struct tuc_corpus *corpus) {
  for (uint32_t case_id = 0U; case_id < TUC_INPUT_CASES; ++case_id) {
    for (uint32_t tensor = 0U; tensor < graph->tensor_count; ++tensor) {
      const uint32_t *input = corpus->inputs[case_id][tensor];
      const uint32_t *output = corpus->outputs[case_id][tensor];
      if ((input != NULL) != tuc_is_input(graph, tensor) ||
          (output != NULL) != tuc_is_output(graph, tensor)) return false;
      for (uint32_t element = 0U; element < graph->tensors[tensor].bytes / 4U; ++element) {
        if ((input != NULL && !tuc_normal_bits(input[element])) ||
            (output != NULL && !tuc_normal_bits(output[element]))) return false;
      }
    }
  }
  return true;
}

static bool tuc_prepare(const struct tuc_plan *plan, struct tuc_storage *storage) {
  for (uint32_t slot = 0U; slot < plan->buffer_count; ++slot) {
    if (!tuc_allocate(&storage->slots[slot], plan->buffers[slot].bytes,
                      plan->buffers[slot].space)) return false;
    storage->owned[slot] = true;
  }
  return true;
}

static bool tuc_finish(const struct tuc_plan *plan, struct tuc_storage *storage) {
  bool ok = true;
  for (uint32_t slot = 0U; slot < plan->buffer_count; ++slot) {
    if (storage->owned[slot])
      ok = tuc_release(storage->slots[slot], plan->buffers[slot].space) && ok;
    storage->owned[slot] = false;
    storage->slots[slot] = NULL;
  }
  return ok;
}

static bool tuc_slot_valid(const struct tuc_graph *graph, const struct tuc_plan *plan,
                           const struct tuc_storage *storage, uint32_t slot) {
  if (slot >= plan->buffer_count || !storage->owned[slot] || storage->slots[slot] == NULL)
    return false;
  const struct tuc_buffer *buffer = &plan->buffers[slot];
  return buffer->tensor < graph->tensor_count && buffer->space <= 1U &&
         buffer->bytes == graph->tensors[buffer->tensor].bytes &&
         buffer->bytes > 0U && buffer->bytes % 4U == 0U &&
         buffer->bytes <= TUC_MAX_BUFFER_BYTES;
}

static const char *tuc_check_result(const float *source, uint32_t bytes, uint32_t space,
                                   struct tuc_counts *counts) {
  float snapshot[TUC_MAX_BUFFER_BYTES / 4U];
  const float *values = source;
  if (space == 1U) {
    if (!tuc_validation_read(snapshot, source, bytes, space)) return "execution_error";
    ++counts->validation_download_calls;
    counts->validation_download_bytes += bytes;
    values = snapshot;
  }
  for (uint32_t i = 0U; i < bytes / 4U; ++i) {
    uint32_t bits;
    memcpy(&bits, values + i, sizeof(bits));
    if (!tuc_normal_bits(bits)) return "numeric_mismatch";
  }
  return "none";
}

static const char *tuc_run(const struct tuc_graph *graph, const struct tuc_plan *plan,
                           const struct tuc_corpus *corpus, struct tuc_storage *storage,
                           uint32_t case_id, struct tuc_counts *counts) {
  bool ready[TUC_MAX_BUFFERS] = {false};
  bool published[TUC_MAX_TENSORS] = {false};
  bool skipped_operation = false, skipped_copy = false, first_publication = true;
  (void)skipped_operation; (void)skipped_copy; (void)first_publication;
  for (uint32_t slot = 0U; slot < plan->buffer_count; ++slot) {
    if (!tuc_slot_valid(graph, plan, storage, slot) ||
        !tuc_poison(storage->slots[slot], plan->buffers[slot].bytes,
                    plan->buffers[slot].space)) return "execution_error";
  }
  for (uint32_t i = 0U; i < plan->event_count; ++i) {
    const struct tuc_event *event = &plan->events[i];
    if (event->kind == 0U) {
      if (!tuc_slot_valid(graph, plan, storage, event->output) || ready[event->output])
        return "execution_error";
      const struct tuc_buffer *out = &plan->buffers[event->output];
      if (out->space != 0U || !tuc_is_input(graph, out->tensor) ||
          corpus->inputs[case_id][out->tensor] == NULL) return "execution_error";
      memcpy(storage->slots[event->output], corpus->inputs[case_id][out->tensor], out->bytes);
      ready[event->output] = true;
    } else if (event->kind == 1U) {
      if (!tuc_slot_valid(graph, plan, storage, event->input0) ||
          !tuc_slot_valid(graph, plan, storage, event->output)) return "execution_error";
      if (!ready[event->input0]) return "missing_operand";
      if (ready[event->output]) return "execution_error";
      const struct tuc_buffer *in = &plan->buffers[event->input0];
      const struct tuc_buffer *out = &plan->buffers[event->output];
      if (in->tensor != out->tensor || in->bytes != out->bytes || in->space == out->space)
        return "execution_error";
#if TUC_FAULT == 4
      if (!skipped_copy) { skipped_copy = true; continue; }
#endif
      if (!tuc_copy(storage->slots[event->output], storage->slots[event->input0], out->bytes,
                    out->space, in->space)) return "execution_error";
      if (out->space == 1U) { ++counts->upload_calls; counts->upload_bytes += out->bytes; }
      else { ++counts->download_calls; counts->download_bytes += out->bytes; }
      ready[event->output] = true;
    } else if (event->kind == 2U) {
      if (event->operation >= graph->op_count || event->target > 1U ||
          event->target != plan->targets[event->operation] ||
          !tuc_slot_valid(graph, plan, storage, event->input0) ||
          !tuc_slot_valid(graph, plan, storage, event->output)) return "execution_error";
      const struct tuc_op *op = &graph->operations[event->operation];
      const struct tuc_buffer *out = &plan->buffers[event->output];
      if (plan->buffers[event->input0].tensor != op->input0 || out->tensor != op->output ||
          plan->buffers[event->input0].space != event->target || out->space != event->target ||
          ready[event->output]) return "execution_error";
      if (!ready[event->input0]) return "missing_operand";
      const float *second = NULL;
      if (op->input1 != TUC_NONE) {
        if (!tuc_slot_valid(graph, plan, storage, event->input1) ||
            plan->buffers[event->input1].tensor != op->input1 ||
            plan->buffers[event->input1].space != event->target) return "execution_error";
        if (!ready[event->input1]) return "missing_operand";
        second = storage->slots[event->input1];
      } else if (event->input1 != TUC_NONE) return "execution_error";
#if TUC_FAULT == 1
      if (!skipped_operation) { skipped_operation = true; continue; }
#endif
      if (!tuc_dispatch(event->target, plan->graph, event->operation,
                        storage->slots[event->input0], second, storage->slots[event->output]))
        return "execution_error";
      if (event->target == 0U) ++counts->cpu_calls;
      else ++counts->gpu_calls;
      const char *checked = tuc_check_result(storage->slots[event->output], out->bytes,
                                             out->space, counts);
      if (strcmp(checked, "none") != 0) return checked;
      ready[event->output] = true;
    } else if (event->kind == 3U) {
      if (!tuc_slot_valid(graph, plan, storage, event->input0)) return "execution_error";
      if (!ready[event->input0]) return "missing_operand";
      const struct tuc_buffer *in = &plan->buffers[event->input0];
      if (in->space != 0U || !tuc_is_output(graph, in->tensor) || published[in->tensor] ||
          corpus->outputs[case_id][in->tensor] == NULL) return "execution_error";
#if TUC_FAULT == 3
      if (first_publication) { first_publication = false; continue; }
#endif
#if TUC_FAULT == 2
      if (first_publication) {
        uint32_t corrupted;
        memcpy(&corrupted, storage->slots[event->input0], sizeof(corrupted));
        corrupted ^= UINT32_C(1);
        memcpy(storage->slots[event->input0], &corrupted, sizeof(corrupted));
        first_publication = false;
      }
#endif
      for (uint32_t element = 0U; element < in->bytes / 4U; ++element) {
        uint32_t actual;
        const uint32_t expected = corpus->outputs[case_id][in->tensor][element];
        memcpy(&actual, storage->slots[event->input0] + element, sizeof(actual));
        const bool both_zero = (actual & UINT32_C(0x7fffffff)) == 0U &&
                               (expected & UINT32_C(0x7fffffff)) == 0U;
        if (!tuc_normal_bits(actual) || (actual != expected && !both_zero))
          return "numeric_mismatch";
        ++counts->scalar_checks;
      }
      published[in->tensor] = true;
      ++counts->published_outputs;
    } else return "execution_error";
  }
  for (uint32_t i = 0U; i < graph->output_count; ++i)
    if (!published[graph->output_ids[i]]) return "missing_publication";
  ++counts->case_runs;
  return "none";
}

static int tuc_emit(uint32_t index, const char *mode, const char *reason,
                     const struct tuc_counts *counts) {
  const bool passed = strcmp(reason, "none") == 0;
  const char *digest = index < TUC_PLAN_COUNT ? tuc_plan_digests[index] : "none";
  printf("{\"schema_version\":\"tuc.bounded_dag_native_observation.v0\","
         "\"worker\":\"%s\",\"plan_index\":%" PRIu32 ",\"plan_digest\":\"%s\","
         "\"mode\":\"%s\",\"status\":\"%s\",\"reason\":\"%s\","
         "\"case_runs\":%" PRIu32 ",\"cpu_calls\":%" PRIu32 ",\"gpu_calls\":%" PRIu32 ","
         "\"scalar_checks\":%" PRIu32 ",\"published_outputs\":%" PRIu32 ","
         "\"upload_calls\":%" PRIu32 ",\"upload_bytes\":%" PRIu32 ","
         "\"download_calls\":%" PRIu32 ",\"download_bytes\":%" PRIu32 ","
         "\"validation_download_calls\":%" PRIu32 ",\"validation_download_bytes\":%" PRIu32 "}\n",
         TUC_WORKER, index, digest, mode, passed ? "PASS" : "ERROR", reason,
         counts->case_runs, counts->cpu_calls, counts->gpu_calls, counts->scalar_checks,
         counts->published_outputs, counts->upload_calls, counts->upload_bytes,
         counts->download_calls, counts->download_bytes, counts->validation_download_calls,
         counts->validation_download_bytes);
  if (passed) return 0;
  if (strcmp(reason, "missing_operand") == 0 || strcmp(reason, "numeric_mismatch") == 0 ||
      strcmp(reason, "missing_publication") == 0) return 1;
  return 2;
}

int main(int argc, char **argv) {
  alarm(20U);
  struct tuc_counts counts = {0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U};
  uint32_t selected = TUC_NONE;
  if (argc != 3 || !tuc_selector(argv[1], &selected))
    return tuc_emit(TUC_NONE, "invalid", "invalid_invocation", &counts);
  const bool execute = strcmp(argv[2], "--execute") == 0;
  const bool preflight = strcmp(argv[2], "--preflight") == 0;
  if (!execute && !preflight)
    return tuc_emit(TUC_NONE, "invalid", "invalid_invocation", &counts);
  const char *mode = execute ? "execute" : "preflight";
  const struct tuc_plan *plan = &tuc_plans[selected];
  if (plan->graph >= TUC_GRAPH_COUNT || !tuc_profile_supported(plan))
    return tuc_emit(selected, mode, "invalid_plan", &counts);
  const struct tuc_graph *graph = &tuc_graphs[plan->graph];
  const struct tuc_corpus *corpus = &tuc_corpora[plan->graph];
  if (!tuc_validate_plan(graph, plan, &tuc_plans[selected]) || !tuc_corpus_valid(graph, corpus))
    return tuc_emit(selected, mode, "invalid_plan", &counts);
  if (!tuc_security_ok())
    return tuc_emit(selected, mode, "security_boundary_mismatch", &counts);
  if (!tuc_float_environment() || !tuc_target_ready(plan))
    return tuc_emit(selected, mode, "target_not_ready", &counts);
  if (preflight) return tuc_emit(selected, mode, "none", &counts);
  struct tuc_storage storage = {{0}, {false}};
  if (!tuc_prepare(plan, &storage)) {
    const bool cleaned = tuc_finish(plan, &storage);
    return tuc_emit(selected, mode, cleaned ? "allocation_failed" : "cleanup_failed", &counts);
  }
  const char *reason = "none";
  for (uint32_t case_id = 0U; case_id < TUC_INPUT_CASES && strcmp(reason, "none") == 0; ++case_id)
    for (uint32_t replay = 0U; replay < TUC_REPLAYS && strcmp(reason, "none") == 0; ++replay)
      reason = tuc_run(graph, plan, corpus, &storage, case_id, &counts);
  if (!tuc_finish(plan, &storage)) reason = "cleanup_failed";
  return tuc_emit(selected, mode, reason, &counts);
}
#endif
