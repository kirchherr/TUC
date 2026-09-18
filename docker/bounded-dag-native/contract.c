#include "abi.h"

_Static_assert(TUC_PLAN_COUNT == 3U * TUC_GRAPH_COUNT, "three profiles per graph required");
_Static_assert(TUC_NONE > TUC_MAX_TENSORS && TUC_NONE > TUC_MAX_OPS &&
               TUC_NONE > TUC_MAX_BUFFERS, "sentinel must not be a valid index");

/* Only compiled, owned structures enter this boundary. No serialized pointers,
 * strings, device handles, or runtime-selected code are accepted. */
static bool tensor_equal(const struct tuc_tensor *a, const struct tuc_tensor *b) {
  return a->rank == b->rank && a->dim0 == b->dim0 && a->dim1 == b->dim1 &&
         a->bytes == b->bytes;
}

static bool op_equal(const struct tuc_op *a, const struct tuc_op *b) {
  return a->kind == b->kind && a->input0 == b->input0 && a->input1 == b->input1 &&
         a->output == b->output && a->blocks == b->blocks && a->threads == b->threads;
}

static bool graph_equal(const struct tuc_graph *a, const struct tuc_graph *b) {
  if (a->tensor_count != b->tensor_count || a->op_count != b->op_count ||
      a->input_count != b->input_count || a->output_count != b->output_count) return false;
  for (uint32_t i = 0U; i < TUC_MAX_TENSORS; ++i)
    if (!tensor_equal(&a->tensors[i], &b->tensors[i])) return false;
  for (uint32_t i = 0U; i < TUC_MAX_OPS; ++i)
    if (!op_equal(&a->operations[i], &b->operations[i])) return false;
  for (uint32_t i = 0U; i < 3U; ++i)
    if (a->input_ids[i] != b->input_ids[i]) return false;
  for (uint32_t i = 0U; i < 2U; ++i)
    if (a->output_ids[i] != b->output_ids[i]) return false;
  return true;
}

static bool plan_equal(const struct tuc_plan *a, const struct tuc_plan *b) {
  if (a->graph != b->graph || a->profile != b->profile ||
      a->buffer_count != b->buffer_count || a->event_count != b->event_count ||
      a->buffer_bytes != b->buffer_bytes || a->copy_bytes != b->copy_bytes) return false;
  for (uint32_t i = 0U; i < TUC_MAX_OPS; ++i)
    if (a->targets[i] != b->targets[i]) return false;
  for (uint32_t i = 0U; i < TUC_MAX_BUFFERS; ++i) {
    const struct tuc_buffer x = a->buffers[i], y = b->buffers[i];
    if (x.tensor != y.tensor || x.space != y.space || x.bytes != y.bytes) return false;
  }
  for (uint32_t i = 0U; i < TUC_MAX_EVENTS; ++i) {
    const struct tuc_event x = a->events[i], y = b->events[i];
    if (x.kind != y.kind || x.operation != y.operation || x.target != y.target ||
        x.input0 != y.input0 || x.input1 != y.input1 || x.output != y.output) return false;
  }
  return true;
}

static bool same_shape(const struct tuc_tensor *a, const struct tuc_tensor *b) {
  return a->rank == b->rank && a->dim0 == b->dim0 && a->dim1 == b->dim1;
}

static bool graph_valid(const struct tuc_graph *graph) {
  if (graph->tensor_count == 0U || graph->tensor_count > TUC_MAX_TENSORS ||
      graph->op_count == 0U || graph->op_count > TUC_MAX_OPS ||
      graph->input_count == 0U || graph->input_count > 3U ||
      graph->output_count == 0U || graph->output_count > 2U) return false;
  bool produced[TUC_MAX_TENSORS] = {false};
  bool consumed[TUC_MAX_TENSORS] = {false};
  bool available[TUC_MAX_TENSORS] = {false};
  bool outputs[TUC_MAX_TENSORS] = {false};
  uint32_t work = 0U;
  for (uint32_t i = 0U; i < graph->tensor_count; ++i) {
    const struct tuc_tensor t = graph->tensors[i];
    if ((t.rank != 1U && t.rank != 2U) || t.dim0 == 0U || t.dim0 > 64U ||
        t.dim1 == 0U || t.dim1 > 64U || (t.rank == 1U && t.dim1 != 1U) ||
        t.bytes != 4U * t.dim0 * t.dim1) return false;
  }
  /* Collect every producer before following any operand. An unknown producer
   * cannot accidentally be reinterpreted as an external input or forward use. */
  for (uint32_t i = 0U; i < graph->op_count; ++i) {
    const struct tuc_op op = graph->operations[i];
    if (op.kind > 2U || op.input0 >= graph->tensor_count ||
        op.output >= graph->tensor_count || produced[op.output] ||
        (op.kind == 0U ? op.input1 >= graph->tensor_count : op.input1 != TUC_NONE))
      return false;
    produced[op.output] = true;
    consumed[op.input0] = true;
    if (op.kind == 0U) consumed[op.input1] = true;
  }
  for (uint32_t i = 0U; i < graph->input_count; ++i) {
    const uint32_t tensor = graph->input_ids[i];
    if (tensor >= graph->tensor_count || produced[tensor] || available[tensor]) return false;
    available[tensor] = true;
  }
  for (uint32_t i = 0U; i < graph->op_count; ++i) {
    const struct tuc_op op = graph->operations[i];
    const struct tuc_tensor a = graph->tensors[op.input0];
    const struct tuc_tensor out = graph->tensors[op.output];
    if (!available[op.input0] || available[op.output] ||
        op.blocks != (out.dim0 * out.dim1 + 127U) / 128U || op.threads != 128U)
      return false;
    if (op.kind == 0U) {
      const struct tuc_tensor b = graph->tensors[op.input1];
      if (!available[op.input1] || a.rank != 2U || b.rank != 2U || out.rank != 2U ||
          a.dim1 != b.dim0 || out.dim0 != a.dim0 || out.dim1 != b.dim1) return false;
      work += 2U * a.dim0 * a.dim1 * b.dim1;
    } else if (op.kind == 1U) {
      if (!same_shape(&a, &out)) return false;
      work += a.dim0 * a.dim1;
    } else {
      if (a.rank != 2U || out.rank != 1U || out.dim0 != a.dim0) return false;
      work += a.dim0 * a.dim1;
    }
    if (work > 1000000U) return false;
    available[op.output] = true;
  }
  for (uint32_t i = 0U; i < graph->output_count; ++i) {
    const uint32_t tensor = graph->output_ids[i];
    if (tensor >= graph->tensor_count || !produced[tensor] || consumed[tensor] ||
        outputs[tensor]) return false;
    outputs[tensor] = true;
  }
  for (uint32_t i = 0U; i < graph->tensor_count; ++i) {
    if (!available[i] || (!produced[i] && !consumed[i]) ||
        (produced[i] && !consumed[i] && !outputs[i])) return false;
  }
  return true;
}

static bool tensor_in(const uint32_t *tensors, uint32_t count, uint32_t tensor) {
  for (uint32_t i = 0U; i < count; ++i) if (tensors[i] == tensor) return true;
  return false;
}

bool tuc_validate_plan(const struct tuc_graph *graph, const struct tuc_plan *plan,
                       const struct tuc_plan *expected) {
  if (graph == NULL || plan == NULL || expected == NULL) return false;
  /* All indices, loop bounds, and arithmetic operands are bounded before use. */
  if (plan->graph >= TUC_GRAPH_COUNT || plan->profile > 2U ||
      plan->buffer_count == 0U || plan->buffer_count > TUC_MAX_BUFFERS ||
      plan->event_count == 0U || plan->event_count > TUC_MAX_EVENTS ||
      plan->buffer_bytes == 0U || plan->buffer_bytes > TUC_MAX_BUFFER_BYTES ||
      plan->copy_bytes > TUC_MAX_COPY_BYTES || !graph_valid(graph)) return false;
  uint32_t total = 0U, copies = 0U, next_op = 0U, input_count = 0U, output_count = 0U;
  bool available[TUC_MAX_BUFFERS] = {false};
  bool bound[TUC_MAX_TENSORS] = {false};
  bool published[TUC_MAX_TENSORS] = {false};
  for (uint32_t i = 0U; i < graph->op_count; ++i) {
    const uint32_t target = plan->profile == 2U ? (i % 2U == 0U ? 1U : 0U) : plan->profile;
    if (plan->targets[i] != target) return false;
  }
  for (uint32_t i = 0U; i < plan->buffer_count; ++i) {
    const struct tuc_buffer b = plan->buffers[i];
    if (b.tensor >= graph->tensor_count || b.space > 1U ||
        b.bytes != graph->tensors[b.tensor].bytes) return false;
    for (uint32_t j = 0U; j < i; ++j) {
      const struct tuc_buffer prior = plan->buffers[j];
      if (b.tensor == prior.tensor && b.space == prior.space) return false;
    }
    total += b.bytes;
    if (total > TUC_MAX_BUFFER_BYTES) return false;
  }
  if (total != plan->buffer_bytes) return false;
  for (uint32_t i = 0U; i < plan->event_count; ++i) {
    const struct tuc_event e = plan->events[i];
    if (e.kind > 3U ||
        (e.kind != 2U && (e.operation != TUC_NONE || e.target != TUC_NONE))) return false;
    if (e.kind == 3U) {
      if (e.input0 >= plan->buffer_count || !available[e.input0] ||
          e.input1 != TUC_NONE || e.output != TUC_NONE || next_op != graph->op_count)
        return false;
      const struct tuc_buffer in = plan->buffers[e.input0];
      if (in.space != 0U || published[in.tensor] ||
          !tensor_in(graph->output_ids, graph->output_count, in.tensor)) return false;
      published[in.tensor] = true;
      ++output_count;
      continue;
    }
    if (e.output >= plan->buffer_count || available[e.output]) return false;
    const struct tuc_buffer out = plan->buffers[e.output];
    if (e.kind == 0U) {
      if (e.input0 != TUC_NONE || e.input1 != TUC_NONE || out.space != 0U ||
          bound[out.tensor] || next_op == graph->op_count ||
          !tensor_in(graph->input_ids, graph->input_count, out.tensor)) return false;
      bound[out.tensor] = true;
      ++input_count;
    } else {
      if (e.input0 >= plan->buffer_count || !available[e.input0]) return false;
      const struct tuc_buffer in = plan->buffers[e.input0];
      if (e.kind == 1U) {
        if (e.input1 != TUC_NONE || in.tensor != out.tensor || in.space == out.space ||
            in.bytes != out.bytes) return false;
        copies += out.bytes;
        if (copies > TUC_MAX_COPY_BYTES) return false;
      } else {
        if (e.operation != next_op || e.operation >= graph->op_count || e.target > 1U ||
            e.target != plan->targets[e.operation]) return false;
        const struct tuc_op op = graph->operations[e.operation];
        if (in.tensor != op.input0 || out.tensor != op.output ||
            in.space != e.target || out.space != e.target) return false;
        if (op.kind == 0U) {
          if (e.input1 >= plan->buffer_count || !available[e.input1]) return false;
          const struct tuc_buffer other = plan->buffers[e.input1];
          if (other.tensor != op.input1 || other.space != e.target) return false;
        } else if (e.input1 != TUC_NONE) return false;
        ++next_op;
      }
    }
    available[e.output] = true;
  }
  if (next_op != graph->op_count || input_count != graph->input_count ||
      output_count != graph->output_count || copies != plan->copy_bytes) return false;
  for (uint32_t i = 0U; i < plan->buffer_count; ++i) if (!available[i]) return false;
  /* Semantic validity is necessary but does not authorize a different valid
   * program. Bind every field, including unused fixed-array entries, to the
   * immutable reviewed descriptors. No structure padding is compared. */
  const uint32_t index = 3U * plan->graph + plan->profile;
  return graph_equal(graph, &tuc_graphs[plan->graph]) &&
         plan_equal(expected, &tuc_plans[index]) && plan_equal(plan, expected);
}
