#ifndef TUC_IO_PLAN_H
#define TUC_IO_PLAN_H
#define TUC_IO_DIGEST "sha256:b0a0a412002c2c6b1d612384dfcce1238f3e3c1a476df329c4f54ae78d486e75"
#define TUC_IO_COUNT 3U
static const unsigned int TUC_BUFFER_BYTES[5] = {924U, 140U, 660U, 660U, 132U};
static const struct tuc_io_step TUC_IO_STEPS[] = {
  {1U, 1U, 0U, 924U, 0U, 1U},
  {1U, 1U, 1U, 140U, 0U, 1U},
  {2U, 2U, 4U, 132U, 1U, 0U},
};
#endif
