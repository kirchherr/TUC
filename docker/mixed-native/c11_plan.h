#ifndef TUC_RESIDENCY_PLAN_H
#define TUC_RESIDENCY_PLAN_H
#define TUC_MIXED 0
#define TUC_RESIDENCY_BYTES 2516U
#define TUC_MIXED_CODE_DIGEST "sha256:88d42c9b13d930d753e003fb30be15db11c3b5942b7e3a8e6f40e4e1ed94f895"
#define TUC_RESIDENCY_DIGEST "sha256:69b7cfd5925cf2b70b6de93ba9a51d15182156757a9c6f5003bd18b0a933e0ef"
#define TUC_BUFFER_COUNT 5U
#define TUC_RESIDENCY_COUNT 6U
static const struct tuc_buffer TUC_BUFFERS[] = {
  {0U, 0U, 924U},
  {1U, 0U, 140U},
  {2U, 0U, 660U},
  {3U, 0U, 660U},
  {4U, 0U, 132U},
};
static const struct tuc_event TUC_EVENTS[] = {
  {0U, 0U, 0U, 255U, 255U, 0U},
  {0U, 0U, 0U, 255U, 255U, 1U},
  {2U, 1U, 0U, 0U, 1U, 2U},
  {2U, 2U, 0U, 2U, 255U, 3U},
  {2U, 3U, 0U, 3U, 255U, 4U},
  {3U, 0U, 0U, 4U, 255U, 255U},
};
#endif
