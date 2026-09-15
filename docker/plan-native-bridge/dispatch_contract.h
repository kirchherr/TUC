#ifndef TUC_DISPATCH_CONTRACT_H
#define TUC_DISPATCH_CONTRACT_H
#include <stdbool.h>
#ifndef TUC_PLAN_FAULT
#define TUC_PLAN_FAULT 0
#endif
struct tuc_step { unsigned int opcode, a, b, out; };
#include TUC_DISPATCH_HEADER

static struct tuc_step plan_step(unsigned int index) {
  struct tuc_step step = TUC_STEPS[index];
#if TUC_PLAN_FAULT == 1
  if (index == 0U) step.opcode = 99U;
#elif TUC_PLAN_FAULT == 2
  if (index == 0U) step = TUC_STEPS[1];
#elif TUC_PLAN_FAULT == 3
  if (index == 0U) step.out = 0U;
#endif
  return step;
}

static bool plan_valid(void) {
  unsigned int count = TUC_STEP_COUNT, target = TUC_PLAN_TARGET;
#if TUC_PLAN_FAULT == 4
  count = 2U;
#elif TUC_PLAN_FAULT == 5
  target = 99U;
#endif
  if (target != TUC_NATIVE_TARGET || count != 3U ||
      sizeof(TUC_STEPS) / sizeof(TUC_STEPS[0]) != 3U) return false;
  bool ready[5] = {true, true, false, false, false};
  bool operations[4] = {false, false, false, false};
  for (unsigned int i = 0U; i < count; ++i) {
    const struct tuc_step s = plan_step(i);
    if (s.opcode < 1U || s.opcode > 3U || operations[s.opcode] ||
        s.a >= 5U || s.out < 2U || s.out >= 5U || !ready[s.a] || ready[s.out]) return false;
    switch (s.opcode) {
      case 1U:
        if (s.a != 0U || s.b != 1U || !ready[s.b] || s.out >= 4U) return false;
        break;
      case 2U:
        if (s.a < 2U || s.a >= 4U || s.b != 5U || s.out >= 4U) return false;
        break;
      case 3U:
        if (s.a < 2U || s.a >= 4U || s.b != 5U || s.out != 4U) return false;
        break;
      default: return false;
    }
    ready[s.out] = true;
    operations[s.opcode] = true;
  }
  return ready[2] && ready[3] && ready[4] && operations[1] && operations[2] && operations[3];
}
#endif
