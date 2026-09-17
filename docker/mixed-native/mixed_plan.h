#ifndef TUC_RESIDENCY_PLAN_H
#define TUC_RESIDENCY_PLAN_H
#define TUC_MIXED 1
#define TUC_RESIDENCY_BYTES 5032U
#define TUC_MIXED_CODE_DIGEST "sha256:88d42c9b13d930d753e003fb30be15db11c3b5942b7e3a8e6f40e4e1ed94f895"
#define TUC_RESIDENCY_DIGEST "sha256:b947de2f33fd608bb9e52111308ff5c3ae67fb3a32fb98a42957c5f9a8e8a6dc"
#define TUC_BUFFER_COUNT 10U
#define TUC_RESIDENCY_COUNT 11U
static const struct tuc_buffer TUC_BUFFERS[] = {
  {0U, 0U, 924U},
  {0U, 1U, 924U},
  {1U, 0U, 140U},
  {1U, 1U, 140U},
  {2U, 1U, 660U},
  {2U, 0U, 660U},
  {3U, 0U, 660U},
  {3U, 1U, 660U},
  {4U, 1U, 132U},
  {4U, 0U, 132U},
};
static const struct tuc_event TUC_EVENTS[] = {
  {0U, 0U, 0U, 255U, 255U, 0U},
  {1U, 0U, 0U, 0U, 255U, 1U},
  {0U, 0U, 0U, 255U, 255U, 2U},
  {1U, 0U, 0U, 2U, 255U, 3U},
  {2U, 1U, 1U, 1U, 3U, 4U},
  {1U, 0U, 0U, 4U, 255U, 5U},
  {2U, 2U, 0U, 5U, 255U, 6U},
  {1U, 0U, 0U, 6U, 255U, 7U},
  {2U, 3U, 1U, 7U, 255U, 8U},
  {1U, 0U, 0U, 8U, 255U, 9U},
  {3U, 0U, 0U, 9U, 255U, 255U},
};
#endif
