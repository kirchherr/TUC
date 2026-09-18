#include "application.h"
#include "seed.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static unsigned long cases;
static uint32_t load(const unsigned char *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static int check(const unsigned char *input, size_t length, int required) {
  unsigned char output[TUC_APPLICATION_RESPONSE_BYTES + 16U];
  memset(output, 0xa5, sizeof(output));
  size_t size = 123U;
  const int code = tuc_application_process(input, length, output,
                                           TUC_APPLICATION_RESPONSE_BYTES, &size);
  if (required >= 0 && code != (required == 3 ? 1 : required)) return 0;
  if (code == 2) { if (size != 0U) return 0; }
  else {
    if ((code != 0 && code != 1) || size < 76U) return 0;
    const uint32_t status = load(output + 72U);
    if (required == 3 && status != 2U) return 0;
    if (memcmp(output, "TUCOUT01", 8U) || memcmp(output + 8U, seed + 8U, 32U) ||
        memcmp(output + 40U, input + 40U, 32U)) return 0;
    if (code == 1) { if (size != 76U || status < 1U || status > 3U) return 0; }
    else {
      if (size != TUC_APPLICATION_RESPONSE_BYTES || status != 0U) return 0;
      for (size_t i = 76U; i < size; i += 4U) {
        const uint32_t bits = load(output + i) & UINT32_C(0x7fffffff);
        const uint32_t exponent = bits & UINT32_C(0x7f800000);
        if (bits != 0U && (exponent == 0U || exponent == UINT32_C(0x7f800000))) return 0;
      }
    }
  }
  for (size_t i = size; i < sizeof(output); ++i) if (output[i] != 0xa5U) return 0;
  ++cases;
  return 1;
}
int main(void) {
  (void)alarm(10U);
  unsigned char input[TUC_APPLICATION_REQUEST_BYTES + 64U];
  unsigned char output[TUC_APPLICATION_RESPONSE_BYTES];
  size_t size = 0U;
  if (tuc_application_process(seed, sizeof(seed), output, sizeof(output), &size) != 0 ||
      size != sizeof(expected) || memcmp(output, expected, sizeof(expected))) return 1;
  ++cases;
  memcpy(input, seed, sizeof(seed));
  memset(input + sizeof(seed), 0, 64U);
  for (size_t i = 0U; i < sizeof(seed); ++i) if (!check(input, i, 2)) return 1;
  for (size_t i = 1U; i <= 64U; ++i) if (!check(input, sizeof(seed) + i, 2)) return 1;
  for (size_t i = 0U; i < sizeof(seed); ++i) {
    for (unsigned int bit = 0U; bit < 8U; ++bit) {
      input[i] ^= (unsigned char)(1U << bit);
      if (!check(input, sizeof(seed), i < 40U ? 2 : i < 72U ? 0 : -1)) return 1;
      input[i] ^= (unsigned char)(1U << bit);
    }
  }
  const uint32_t special[] = {0U, UINT32_C(0x80000000), 1U, UINT32_C(0x007fffff),
    UINT32_C(0x00800000), UINT32_C(0x7f800000), UINT32_C(0xff800000),
    UINT32_C(0x7fc00000), UINT32_C(0x7f800001), UINT32_C(0x7f7fffff)};
  for (size_t i = 72U; i < sizeof(seed); i += 4U) {
    for (size_t k = 0U; k < sizeof(special) / sizeof(special[0]); ++k) {
      for (unsigned int j = 0U; j < 4U; ++j)
        input[i + j] = (unsigned char)((special[k] >> (8U * j)) & 255U);
      const int numeric = k == 2U || k == 3U || (k >= 5U && k <= 8U);
      if (!check(input, sizeof(seed), numeric ? 3 : -1)) return 1;
    }
    memcpy(input + i, seed + i, 4U);
  }
  memset(output, 0xa5, sizeof(output));
  for (size_t capacity = 0U; capacity < sizeof(output); ++capacity) {
    size = 123U;
    if (tuc_application_process(seed, sizeof(seed), output, capacity, &size) != 2 ||
        size != 0U) return 1;
    for (size_t i = 0U; i < sizeof(output); ++i) if (output[i] != 0xa5U) return 1;
    ++cases;
  }
  if (!check(NULL, sizeof(seed), 2)) return 1;
  size = 123U;
  if (tuc_application_process(seed, sizeof(seed), NULL, sizeof(output), &size) != 2 ||
      size != 0U || tuc_application_process(seed, sizeof(seed), output,
                                            sizeof(output), NULL) != 2) return 1;
  cases += 2U;
  printf("{\"status\":\"PASS\",\"program_digest\":\"%s\",\"fuzz_cases\":%lu}\n",
         TUC_APPLICATION_PROGRAM_DIGEST, cases);
  return 0;
}
