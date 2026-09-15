#ifndef TUC_MIXED_WORKER_H
#define TUC_MIXED_WORKER_H
static const float *read_slots[TUC_BUFFER_COUNT] = {0};
static float *write_slots[TUC_BUFFER_COUNT] = {0};
static bool owned[TUC_BUFFER_COUNT] = {false};

static bool prepare(void) {
  for (unsigned int i = 0U; i < TUC_BUFFER_COUNT; ++i) {
    const struct tuc_buffer b = buffer_at(i);
    if (b.space == 0U && (b.tensor < 2U || b.tensor == 4U)) continue;
    if (!allocate_buffer(&write_slots[i], b.bytes, b.space)) return false;
    owned[i] = true;
    read_slots[i] = write_slots[i];
  }
  return true;
}
static bool finish(void) {
  bool ok = true;
  for (unsigned int i = 0U; i < TUC_BUFFER_COUNT; ++i) {
    if (owned[i]) ok = release_buffer(write_slots[i], buffer_at(i).space) && ok;
    owned[i] = false; write_slots[i] = NULL; read_slots[i] = NULL;
  }
  return ok;
}
static bool evaluate(const float *a, const float *b, float *output, unsigned int *calls) {
  bool available[TUC_BUFFER_COUNT] = {false};
  unsigned int completed = 0U;
  const float *inputs[2] = {a, b};
  for (unsigned int i = 0U; i < TUC_BUFFER_COUNT; ++i) {
    const struct tuc_buffer slot = buffer_at(i);
    if (slot.space == 0U && slot.tensor < 2U) read_slots[i] = NULL;
    else {
      if (slot.space == 0U && slot.tensor == 4U) {
        read_slots[i] = output; write_slots[i] = output;
      }
      if (!poison_buffer(write_slots[i], slot.bytes, slot.space)) return false;
    }
  }
  for (unsigned int i = 0U; i < TUC_RESIDENCY_COUNT; ++i) {
    const struct tuc_event s = event_at(i);
    if (s.kind == 0U) {
      read_slots[s.out] = inputs[buffer_at(s.out).tensor];
      available[s.out] = true;
    } else if (s.kind == 1U) {
#ifdef TUC_SKIP_TRANSFER
      if (buffer_at(s.a).tensor == 2U) continue;
#endif
      if (!available[s.a] || available[s.out]) return false;
      const struct tuc_buffer out = buffer_at(s.out);
      if (!copy_buffer(write_slots[s.out], read_slots[s.a], out.bytes, out.space)) return false;
      if (out.space == 1U) { ++upload_calls; upload_bytes += out.bytes; }
      else { ++download_calls; download_bytes += out.bytes; }
      available[s.out] = true;
    } else if (s.kind == 2U) {
      if (!available[s.a] || (s.b != 255U && !available[s.b]) || available[s.out]) return false;
      if (s.space == 0U) {
        switch (s.opcode) {
          case 1U: host_projection(read_slots[s.a], read_slots[s.b], write_slots[s.out]); break;
          case 2U: host_relu(read_slots[s.a], write_slots[s.out]); break;
          case 3U: host_sum(read_slots[s.a], write_slots[s.out]); break;
          default: return false;
        }
        ++cpu_calls;
      } else {
        if (!device_dispatch(s.opcode, read_slots[s.a], s.b == 255U ? NULL : read_slots[s.b],
                             write_slots[s.out])) return false;
        ++gpu_calls;
      }
      ++*calls;
      available[s.out] = true;
    } else {
#ifdef TUC_SKIP_PUBLISH
      continue;
#endif
      if (!available[s.a] || read_slots[s.a] != output) return false;
    }
    ++completed; ++completed_steps;
  }
  return completed == TUC_RESIDENCY_COUNT;
}
#undef TUC_TENSOR_BYTES
#define TUC_TENSOR_BYTES TUC_RESIDENCY_BYTES
#include "common.h"
#endif
