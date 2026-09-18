#ifndef TUC_DAG_NATIVE_ABI_H
#define TUC_DAG_NATIVE_ABI_H
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#define TUC_GRAPH_COUNT 12U
#define TUC_PLAN_COUNT 36U
#define TUC_MAX_TENSORS 10U
#define TUC_MAX_OPS 7U
#define TUC_MAX_BUFFERS 16U
#define TUC_MAX_EVENTS 18U
#define TUC_MAX_BUFFER_BYTES 7432U
#define TUC_MAX_COPY_BYTES 2656U
#define TUC_NONE 255U
#define TUC_INPUT_CASES 3U
#define TUC_REPLAYS 2U
struct tuc_tensor { uint32_t rank, dim0, dim1, bytes; };
struct tuc_op { uint32_t kind, input0, input1, output, blocks, threads; };
struct tuc_buffer { uint32_t tensor, space, bytes; };
struct tuc_event { uint32_t kind, operation, target, input0, input1, output; };
struct tuc_graph {
  uint32_t tensor_count, op_count, input_count, output_count;
  struct tuc_tensor tensors[TUC_MAX_TENSORS];
  struct tuc_op operations[TUC_MAX_OPS];
  uint32_t input_ids[3], output_ids[2];
};
struct tuc_plan {
  uint32_t graph, profile, buffer_count, event_count, buffer_bytes, copy_bytes;
  uint32_t targets[TUC_MAX_OPS];
  struct tuc_buffer buffers[TUC_MAX_BUFFERS];
  struct tuc_event events[TUC_MAX_EVENTS];
};
struct tuc_corpus {
  const uint32_t *inputs[TUC_INPUT_CASES][TUC_MAX_TENSORS];
  const uint32_t *outputs[TUC_INPUT_CASES][TUC_MAX_TENSORS];
};
struct tuc_counts {
  uint32_t case_runs, cpu_calls, gpu_calls, scalar_checks, published_outputs;
  uint32_t upload_calls, upload_bytes, download_calls, download_bytes;
  uint32_t validation_download_calls, validation_download_bytes;
};
#ifdef __cplusplus
extern "C" {
#endif
extern const struct tuc_graph tuc_graphs[TUC_GRAPH_COUNT];
extern const struct tuc_plan tuc_plans[TUC_PLAN_COUNT];
extern const struct tuc_corpus tuc_corpora[TUC_GRAPH_COUNT];
extern const char *const tuc_plan_digests[TUC_PLAN_COUNT];
bool tuc_validate_plan(const struct tuc_graph *graph, const struct tuc_plan *plan,
                       const struct tuc_plan *expected);
bool tuc_host_dispatch(uint32_t graph, uint32_t op, const float *a,
                       const float *b, float *output);
bool tuc_device_dispatch(uint32_t graph, uint32_t op, const float *a,
                         const float *b, float *output);
#ifdef __cplusplus
}
#endif
#endif
