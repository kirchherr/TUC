#ifndef TUC_IO_CONTRACT_H
#define TUC_IO_CONTRACT_H
#include <stdio.h>
#ifndef TUC_IO_FAULT
#define TUC_IO_FAULT 0
#endif
struct tuc_io_step { unsigned int phase, mode, slot, bytes, source, target; };
#include TUC_IO_HEADER
static unsigned int io_completed = 0U, io_bindings = 0U;
static unsigned int io_upload_calls = 0U, io_upload_bytes = 0U;
static unsigned int io_download_calls = 0U, io_download_bytes = 0U;

static struct tuc_io_step io_step(unsigned int index) {
  struct tuc_io_step s = TUC_IO_STEPS[index];
#if TUC_IO_FAULT == 2
  if (index == 0U) s.mode = 2U;
#elif TUC_IO_FAULT == 3
  if (index == 0U) s.bytes += 4U;
#elif TUC_IO_FAULT == 4
  if (index == 0U) s.slot = 1U;
#elif TUC_IO_FAULT == 5
  if (index == 0U) s = TUC_IO_STEPS[2];
#elif TUC_IO_FAULT == 6
  if (index == 1U) s = TUC_IO_STEPS[0];
#elif TUC_IO_FAULT == 7
  if (index == 2U) s.bytes -= 4U;
#endif
  return s;
}

static bool io_valid(void) {
  unsigned int count = TUC_IO_COUNT;
#if TUC_IO_FAULT == 1
  count = 2U;
#endif
  const unsigned int sizes[5] = {924U, 140U, 660U, 660U, 132U};
  if (!plan_valid() || count != 3U || sizeof(TUC_IO_STEPS) / sizeof(TUC_IO_STEPS[0]) != 3U)
    return false;
  for (unsigned int i = 0U; i < 5U; ++i)
    if (TUC_BUFFER_BYTES[i] != sizes[i]) return false;
  for (unsigned int i = 0U; i < count; ++i) {
    const struct tuc_io_step s = io_step(i);
    const unsigned int slot = i < 2U ? i : 4U;
    const unsigned int phase = i < 2U ? 1U : 2U;
    const unsigned int mode = TUC_NATIVE_TARGET == 1U ? 0U : phase;
    const unsigned int src = TUC_NATIVE_TARGET == 2U && phase == 2U ? 1U : 0U;
    const unsigned int dst = TUC_NATIVE_TARGET == 2U && phase == 1U ? 1U : 0U;
    if (s.slot != slot || s.phase != phase || s.mode != mode || s.bytes != sizes[slot] ||
        s.source != src || s.target != dst) return false;
  }
  return true;
}

static void io_emit_metadata(void) {
  printf("{\"schema_version\":\"tuc.bounded_native_io_observation.v0\","
         "\"io_plan_digest\":\"%s\",\"io\":{\"completed_steps\":%u,\"host_bindings\":%u,"
         "\"upload_calls\":%u,\"upload_bytes\":%u,\"download_calls\":%u,\"download_bytes\":%u},"
         "\"numeric_observation\":", TUC_IO_DIGEST, io_completed, io_bindings,
         io_upload_calls, io_upload_bytes, io_download_calls, io_download_bytes);
}
#endif
