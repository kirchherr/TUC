#ifndef TUC_FANOUT_PLANS_H
#define TUC_FANOUT_PLANS_H
#define TUC_MATRIX_CODE_DIGEST "sha256:88d42c9b13d930d753e003fb30be15db11c3b5942b7e3a8e6f40e4e1ed94f895"
static const struct tuc_buffer buffers_cccc[] = {
  {0U, 0U, 924U},
  {1U, 0U, 140U},
  {2U, 0U, 660U},
  {3U, 0U, 660U},
  {4U, 0U, 132U},
  {5U, 0U, 132U},
};
static const struct tuc_event events_cccc[] = {
  {0U, 0U, 0U, 255U, 255U, 0U},
  {0U, 0U, 0U, 255U, 255U, 1U},
  {2U, 1U, 0U, 0U, 1U, 2U},
  {2U, 2U, 0U, 2U, 255U, 3U},
  {2U, 3U, 0U, 2U, 255U, 4U},
  {2U, 4U, 0U, 3U, 255U, 5U},
  {3U, 0U, 0U, 4U, 255U, 255U},
  {3U, 0U, 0U, 5U, 255U, 255U},
};

static const struct tuc_buffer buffers_gccc[] = {
  {0U, 0U, 924U},
  {0U, 1U, 924U},
  {1U, 0U, 140U},
  {1U, 1U, 140U},
  {2U, 1U, 660U},
  {2U, 0U, 660U},
  {3U, 0U, 660U},
  {4U, 0U, 132U},
  {5U, 0U, 132U},
};
static const struct tuc_event events_gccc[] = {
  {0U, 0U, 0U, 255U, 255U, 0U},
  {1U, 0U, 0U, 0U, 255U, 1U},
  {0U, 0U, 0U, 255U, 255U, 2U},
  {1U, 0U, 0U, 2U, 255U, 3U},
  {2U, 1U, 1U, 1U, 3U, 4U},
  {1U, 0U, 0U, 4U, 255U, 5U},
  {2U, 2U, 0U, 5U, 255U, 6U},
  {2U, 3U, 0U, 5U, 255U, 7U},
  {2U, 4U, 0U, 6U, 255U, 8U},
  {3U, 0U, 0U, 7U, 255U, 255U},
  {3U, 0U, 0U, 8U, 255U, 255U},
};

static const struct tuc_buffer buffers_gggg[] = {
  {0U, 0U, 924U},
  {0U, 1U, 924U},
  {1U, 0U, 140U},
  {1U, 1U, 140U},
  {2U, 1U, 660U},
  {3U, 1U, 660U},
  {4U, 1U, 132U},
  {5U, 1U, 132U},
  {4U, 0U, 132U},
  {5U, 0U, 132U},
};
static const struct tuc_event events_gggg[] = {
  {0U, 0U, 0U, 255U, 255U, 0U},
  {1U, 0U, 0U, 0U, 255U, 1U},
  {0U, 0U, 0U, 255U, 255U, 2U},
  {1U, 0U, 0U, 2U, 255U, 3U},
  {2U, 1U, 1U, 1U, 3U, 4U},
  {2U, 2U, 1U, 4U, 255U, 5U},
  {2U, 3U, 1U, 4U, 255U, 6U},
  {2U, 4U, 1U, 5U, 255U, 7U},
  {1U, 0U, 0U, 6U, 255U, 8U},
  {3U, 0U, 0U, 8U, 255U, 255U},
  {1U, 0U, 0U, 7U, 255U, 9U},
  {3U, 0U, 0U, 9U, 255U, 255U},
};

static const struct tuc_profile profiles[] = {
  {"cccc", "sha256:a883e51f9a5a9b5676df938ed93490ede30337898104af63ad6013c9391e5926", 0U, 6U, 8U, 2648U, buffers_cccc, events_cccc},
  {"gccc", "sha256:117a0d88acc14b4fa69dd920b9debb9a08b3409d39a626ed5c1e84fdc8efbdc4", 8U, 9U, 11U, 4372U, buffers_gccc, events_gccc},
  {"gggg", "sha256:3c73cdb726d7440ae1256a6f5c6dfebfb4ec1fbbf04fa45ca9ee40417a2c1d0e", 15U, 10U, 12U, 3976U, buffers_gggg, events_gggg},
};
#endif
