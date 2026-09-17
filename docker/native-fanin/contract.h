#ifndef TUC_FANIN_CONTRACT_H
#define TUC_FANIN_CONTRACT_H
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define TUC_MAX_BUFFERS 9U
#define TUC_MAX_EVENTS 10U
struct tuc_buffer { unsigned int tensor, space, bytes; };
struct tuc_event { unsigned int kind, opcode, space, a, b, out; };
struct tuc_profile {
  const char *name, *digest;
  unsigned int mask, buffer_count, event_count, bytes;
  const struct tuc_buffer *buffers;
  const struct tuc_event *events;
};
#include "plans.h"
static const char *const profile_names[] = {"cccc", "gccc", "cgcc", "gcgg", "cggg", "gggg"};
static const unsigned int masks[] = {0U, 8U, 4U, 11U, 7U, 15U};
static const struct tuc_profile *active = &profiles[0];
static unsigned int selected;
#define TUC_BUFFER_COUNT active->buffer_count
#define TUC_RESIDENCY_COUNT active->event_count
#define TUC_RESIDENCY_BYTES active->bytes
#ifndef TUC_SCHEDULE_FAULT
#define TUC_SCHEDULE_FAULT 0
#endif
static unsigned int completed_steps, cpu_calls, gpu_calls;
static unsigned int upload_calls, upload_bytes, download_calls, download_bytes;
static unsigned int left_producer_calls, right_producer_calls, join_calls;
static unsigned int left_copy_calls, right_copy_calls, published_outputs;

static bool select_profile(const char *name) {
  for (unsigned int i = 0U; i < 6U; ++i)
    if (strcmp(name, profile_names[i]) == 0) { selected = i; active = &profiles[i]; return true; }
  return false;
}
static struct tuc_buffer buffer_at(unsigned int i) {
  struct tuc_buffer b = active->buffers[i];
#if TUC_SCHEDULE_FAULT == 3
  if (i == 0U) b.space = 1U;
#elif TUC_SCHEDULE_FAULT == 5
  if (i == 0U) b.bytes += 4U;
#endif
  return b;
}
static struct tuc_event event_at(unsigned int i) {
  struct tuc_event e = active->events[i];
#if TUC_SCHEDULE_FAULT == 2
  if (i == 0U) e.out = 255U;
#elif TUC_SCHEDULE_FAULT == 4
  if (i == 0U) e = active->events[TUC_RESIDENCY_COUNT - 1U];
#elif TUC_SCHEDULE_FAULT == 6
  if (i == TUC_RESIDENCY_COUNT - 1U) e = active->events[0];
#elif TUC_SCHEDULE_FAULT == 7
  if (e.kind == 2U) e.space ^= 1U;
#elif TUC_SCHEDULE_FAULT == 8
  if (e.kind == 2U && e.opcode == 3U) e.a = e.b;
#elif TUC_SCHEDULE_FAULT == 9
  if (e.kind == 2U && e.opcode == 3U) e.b = e.a;
#elif TUC_SCHEDULE_FAULT == 10
  if (e.kind == 2U && e.opcode == 3U) { const unsigned int a = e.a; e.a = e.b; e.b = a; }
#endif
  return e;
}
static bool schedule_valid(void) {
  if (selected >= 6U || active->mask != masks[selected] || strcmp(active->name, profile_names[selected]) != 0)
    return false;
  const unsigned int sizes[6] = {924U, 140U, 924U, 140U, 660U, 132U};
  const unsigned int copies[6] = {0U, 2U, 2U, 3U, 3U, 3U};
  const unsigned int bytes[6] = {2920U, 4768U, 3200U, 4116U, 4116U, 4116U};
  const unsigned int input_tensor[4] = {0U, 1U, 2U, 4U};
  unsigned int count = TUC_RESIDENCY_COUNT, stage = 0U, published = 0U, total = 0U;
  bool bound[2] = {false}, available[TUC_MAX_BUFFERS] = {false};
#if TUC_SCHEDULE_FAULT == 1
  --count;
#endif
  if (TUC_BUFFER_COUNT != 6U + copies[selected] || count != 7U + copies[selected] ||
      TUC_BUFFER_COUNT > TUC_MAX_BUFFERS || count > TUC_MAX_EVENTS ||
      TUC_RESIDENCY_BYTES != bytes[selected]) return false;
  for (unsigned int i = 0U; i < TUC_BUFFER_COUNT; ++i) {
    const struct tuc_buffer b = buffer_at(i);
    if (b.tensor >= 6U || b.space > 1U || b.bytes != sizes[b.tensor]) return false;
    for (unsigned int j = 0U; j < i; ++j)
      if (b.tensor == buffer_at(j).tensor && b.space == buffer_at(j).space) return false;
    total += b.bytes;
  }
  if (total != bytes[selected]) return false;
  for (unsigned int i = 0U; i < count; ++i) {
    const struct tuc_event e = event_at(i);
    if (e.kind > 3U || e.space > 1U || (e.kind != 2U && (e.opcode != 0U || e.space != 0U))) return false;
    if (e.kind == 3U) {
      if (published != 0U || stage != 4U || e.a >= TUC_BUFFER_COUNT || !available[e.a] ||
          buffer_at(e.a).tensor != 5U || buffer_at(e.a).space != 0U ||
          e.b != 255U || e.out != 255U || i != count - 1U) return false;
      ++published; continue;
    }
    if (e.out >= TUC_BUFFER_COUNT || available[e.out]) return false;
    const struct tuc_buffer out = buffer_at(e.out);
    if (e.kind == 0U) {
      if (out.tensor >= 2U || out.space != 0U || e.a != 255U || e.b != 255U ||
          bound[out.tensor] || stage != out.tensor) return false;
      bound[out.tensor] = true;
    } else {
      if (e.a >= TUC_BUFFER_COUNT || !available[e.a]) return false;
      const struct tuc_buffer a = buffer_at(e.a);
      if (e.kind == 1U) {
        if (e.b != 255U || a.tensor != out.tensor || a.space == out.space || a.bytes != out.bytes) return false;
      } else {
        if (e.opcode != stage + 1U || e.opcode > 4U || out.tensor != e.opcode + 1U ||
            a.tensor != input_tensor[e.opcode - 1U] ||
            e.space != ((active->mask >> (4U - e.opcode)) & 1U) ||
            a.space != e.space || out.space != e.space) return false;
        if (e.opcode == 3U) {
          if (e.b >= TUC_BUFFER_COUNT || !available[e.b] || buffer_at(e.b).tensor != 3U ||
              buffer_at(e.b).space != e.space || e.a == e.b) return false;
        } else if (e.b != 255U) return false;
        ++stage;
      }
    }
    available[e.out] = true;
  }
  for (unsigned int i = 0U; i < TUC_BUFFER_COUNT; ++i) if (!available[i]) return false;
  return stage == 4U && published == 1U && bound[0] && bound[1];
}
static void residency_emit(void) {
  printf("{\"schema_version\":\"tuc.bounded_fanin_observation.v0\","
         "\"worker\":\"%s\",\"profile\":\"%s\",\"plan_digest\":\"%s\","
         "\"residency\":{\"completed_steps\":%u,\"cpu_calls\":%u,\"gpu_calls\":%u,"
         "\"upload_calls\":%u,\"upload_bytes\":%u,\"download_calls\":%u,\"download_bytes\":%u,"
         "\"left_producer_calls\":%u,\"right_producer_calls\":%u,\"join_calls\":%u,"
         "\"left_copy_calls\":%u,\"right_copy_calls\":%u,\"published_outputs\":%u},"
         "\"numeric_observation\":",
         TUC_WORKER, active->name, active->digest, completed_steps, cpu_calls, gpu_calls,
         upload_calls, upload_bytes, download_calls, download_bytes,
         left_producer_calls, right_producer_calls, join_calls,
         left_copy_calls, right_copy_calls, published_outputs);
}
#endif
