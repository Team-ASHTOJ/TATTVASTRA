#include "jocky/runtime.h"
#include <gtest/gtest.h>

TEST(RuntimeBoundary, VersionIsExplicit) {
  EXPECT_EQ(jocky_rt_abi_version(), JOCKY_RUNTIME_ABI_VERSION);
}

TEST(RuntimeBoundary, MissingContextCannotProduceEvidence) {
  jocky_dataset_handle handle = 99;
  EXPECT_EQ(jocky_rt_process_list(nullptr, &handle), JOCKY_INVALID_ARGUMENT);
  EXPECT_EQ(handle, 0u);
  EXPECT_EQ(jocky_rt_system_info(nullptr, nullptr), JOCKY_INVALID_ARGUMENT);
}
