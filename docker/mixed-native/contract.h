#ifndef TUC_MIXED_CONTRACT_H
#define TUC_MIXED_CONTRACT_H
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
struct tuc_buffer { unsigned int tensor, space, bytes; };
struct tuc_event { unsigned int kind, opcode, space, a, b, out; };
#include TUC_PLAN_HEADER
#ifndef TUC_SCHEDULE_FAULT
#define TUC_SCHEDULE_FAULT 0
#endif
static unsigned int completed_steps, cpu_calls, gpu_calls;
static unsigned int upload_calls, upload_bytes, download_calls, download_bytes;

static struct tuc_buffer buffer_at(unsigned int i) {
  struct tuc_buffer b = TUC_BUFFERS[i];
#if TUC_SCHEDULE_FAULT == 3
  if (i == 0U) b.space = 1U;
#elif TUC_SCHEDULE_FAULT == 5
  if (i == 0U) b.bytes += 4U;
#endif
  return b;
}
static struct tuc_event event_at(unsigned int i) {
  struct tuc_event s = TUC_EVENTS[i];
#if TUC_SCHEDULE_FAULT == 2
  if (i == 0U) s.out = 255U;
#elif TUC_SCHEDULE_FAULT == 4
  if (i == 0U) s = TUC_EVENTS[TUC_RESIDENCY_COUNT - 1U];
#elif TUC_SCHEDULE_FAULT == 6
  if (i == TUC_RESIDENCY_COUNT - 1U) s = TUC_EVENTS[0];
#endif
  return s;
}
static bool schedule_valid(void) {
  const unsigned int sizes[5] = {924U, 140U, 660U, 660U, 132U};
  const unsigned int expected_buffers = TUC_MIXED ? 10U : 5U;
  const unsigned int expected_events = TUC_MIXED ? 11U : 6U;
  unsigned int count = TUC_RESIDENCY_COUNT, stage = 0U, published = 0U, total = 0U;
#if TUC_SCHEDULE_FAULT == 1
  --count;
#endif
  if (TUC_BUFFER_COUNT != expected_buffers || count != expected_events ||
      sizeof(TUC_BUFFERS) / sizeof(TUC_BUFFERS[0]) != expected_buffers ||
      sizeof(TUC_EVENTS) / sizeof(TUC_EVENTS[0]) != expected_events) return false;
  bool available[TUC_BUFFER_COUNT] = {false};
  for (unsigned int i = 0U; i < TUC_BUFFER_COUNT; ++i) {
    const struct tuc_buffer b = buffer_at(i);
    if (b.tensor >= 5U || b.space > (TUC_MIXED ? 1U : 0U) || b.bytes != sizes[b.tensor])
      return false;
    for (unsigned int j = 0U; j < i; ++j)
      if (b.tensor == buffer_at(j).tensor && b.space == buffer_at(j).space) return false;
    total += b.bytes;
  }
  if (total != TUC_RESIDENCY_BYTES) return false;
  for (unsigned int i = 0U; i < count; ++i) {
    const struct tuc_event s = event_at(i);
    if (s.kind > 3U || s.space > 1U || (s.kind != 2U && (s.opcode != 0U || s.space != 0U)))
      return false;
    if (s.kind == 3U) {
      if (s.a >= TUC_BUFFER_COUNT || !available[s.a] || buffer_at(s.a).tensor != 4U ||
          buffer_at(s.a).space != 0U || s.b != 255U || s.out != 255U || stage != 3U ||
          i != count - 1U) return false;
      ++published;
      continue;
    }
    if (s.out >= TUC_BUFFER_COUNT || available[s.out]) return false;
    const struct tuc_buffer out = buffer_at(s.out);
    if (s.kind == 0U) {
      if (out.tensor >= 2U || out.space != 0U || s.a != 255U || s.b != 255U || stage != 0U)
        return false;
    } else {
      if (s.a >= TUC_BUFFER_COUNT || !available[s.a]) return false;
      const struct tuc_buffer a = buffer_at(s.a);
      if (s.kind == 1U) {
        if (s.b != 255U || a.tensor != out.tensor || a.space == out.space || a.bytes != out.bytes)
          return false;
      } else {
        if (s.opcode != stage + 1U || s.opcode > 3U || out.tensor != s.opcode + 1U ||
            s.space != (TUC_MIXED && s.opcode != 2U ? 1U : 0U) ||
            a.space != s.space || out.space != s.space) return false;
        if (s.opcode == 1U) {
          if (a.tensor != 0U || s.b >= TUC_BUFFER_COUNT || !available[s.b] ||
              buffer_at(s.b).tensor != 1U || buffer_at(s.b).space != s.space) return false;
        } else if (a.tensor != s.opcode || s.b != 255U) return false;
        ++stage;
      }
    }
    available[s.out] = true;
  }
  for (unsigned int i = 0U; i < TUC_BUFFER_COUNT; ++i) if (!available[i]) return false;
  return stage == 3U && published == 1U;
}
static void residency_emit(void) {
  printf("{\"schema_version\":\"tuc.bounded_mixed_native_observation.v0\","
         "\"plan_digest\":\"%s\",\"residency\":{\"completed_steps\":%u,"
         "\"cpu_calls\":%u,\"gpu_calls\":%u,\"upload_calls\":%u,\"upload_bytes\":%u,"
         "\"download_calls\":%u,\"download_bytes\":%u},\"numeric_observation\":",
         TUC_RESIDENCY_DIGEST, completed_steps, cpu_calls, gpu_calls,
         upload_calls, upload_bytes, download_calls, download_bytes);
}
#endif
