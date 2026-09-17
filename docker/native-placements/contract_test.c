#define TUC_WORKER "contract-test"
#include "contract.h"
#include <assert.h>
#include <limits.h>

int main(void) {
  (void)residency_emit;
  unsigned int probes = 0U;
  assert(!select_profile("ccc-extra"));
  assert(!select_profile(""));
  assert(!select_profile("../ccc"));
  assert(!select_profile("CCC"));
  for (unsigned int p = 0U; p < 8U; ++p) {
    assert(select_profile(profile_names[p]) && schedule_valid());
    struct tuc_profile copy = profiles[p];
    struct tuc_buffer buffers[TUC_MAX_BUFFERS];
    struct tuc_event events[TUC_MAX_EVENTS];
    memcpy(buffers, copy.buffers, copy.buffer_count * sizeof(buffers[0]));
    memcpy(events, copy.events, copy.event_count * sizeof(events[0]));
    copy.buffers = buffers; copy.events = events; active = &copy;
    for (unsigned int bit = 0U; bit < sizeof(unsigned int) * CHAR_BIT; ++bit) {
      const unsigned int delta = 1U << bit;
      unsigned int *const counts[] = {&copy.mask, &copy.buffer_count, &copy.event_count, &copy.bytes};
      for (unsigned int i = 0U; i < 4U; ++i) {
        *counts[i] ^= delta; assert(!schedule_valid()); *counts[i] ^= delta; ++probes;
      }
      for (unsigned int i = 0U; i < copy.buffer_count; ++i) {
        unsigned int *const fields[] = {&buffers[i].tensor, &buffers[i].space, &buffers[i].bytes};
        for (unsigned int j = 0U; j < 3U; ++j) {
          *fields[j] ^= delta; assert(!schedule_valid()); *fields[j] ^= delta; ++probes;
        }
      }
      for (unsigned int i = 0U; i < copy.event_count; ++i) {
        unsigned int *const fields[] = {&events[i].kind, &events[i].opcode, &events[i].space,
                                       &events[i].a, &events[i].b, &events[i].out};
        for (unsigned int j = 0U; j < 6U; ++j) {
          *fields[j] ^= delta; assert(!schedule_valid()); *fields[j] ^= delta; ++probes;
        }
      }
    }
    assert(schedule_valid());
    active = &profiles[p];
  }
  printf("{\"schema_version\":\"tuc.placement_contract_sanitizer.v0\","
         "\"profiles_checked\":8,\"invalid_selectors\":4,\"bitflip_rejections\":%u,\"status\":\"PASS\"}\n", probes);
  return 0;
}
