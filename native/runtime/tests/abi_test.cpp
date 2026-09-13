#include "jocky/runtime.h"
#include <gtest/gtest.h>
#include <string>

TEST(RuntimeBoundary, VersionAndOwnershipAreExplicit) {
  EXPECT_EQ(jocky_rt_abi_version(), JOCKY_RUNTIME_ABI_VERSION);
  jocky_context *context = nullptr;
  ASSERT_EQ(jocky_rt_fixture_context_create(&context), JOCKY_OK);
  ASSERT_NE(context, nullptr);
  EXPECT_EQ(jocky_rt_fixture_is_simulation(context), 1);
  jocky_dataset_handle handle = 0;
  EXPECT_EQ(jocky_rt_system_info(context, 0, nullptr, 0, &handle), JOCKY_OK);
  EXPECT_NE(handle, JOCKY_DATASET_INVALID);
  EXPECT_EQ(jocky_rt_dataset_retain(context, handle), JOCKY_OK);
  EXPECT_EQ(jocky_rt_dataset_release(context, handle), JOCKY_OK);
  EXPECT_EQ(jocky_rt_dataset_release(context, handle), JOCKY_OK);
  jocky_rt_context_destroy(context);
}

TEST(RuntimeBoundary, MissingContextCannotProduceEvidence) {
  jocky_dataset_handle handle = 99;
  EXPECT_EQ(jocky_rt_processes(nullptr, 0, nullptr, 0, &handle), JOCKY_INVALID_ARGUMENT);
  EXPECT_EQ(handle, 0u);
  EXPECT_EQ(jocky_rt_system_info(nullptr, 0, nullptr, 0, nullptr), JOCKY_INVALID_ARGUMENT);
}

TEST(RuntimeBoundary, DynamicOpcodeIsClosedAndFixtureHashIsReal) {
  jocky_context *context = nullptr;
  ASSERT_EQ(jocky_rt_fixture_context_create(&context), JOCKY_OK);
  jocky_dataset_handle handle = 0;
  const std::string bad = "SHELL_EXECUTE";
  EXPECT_EQ(jocky_rt_analysis(context, 0, bad.data(), bad.size(), nullptr, 0, nullptr, 0, &handle),
            JOCKY_INVALID_ARGUMENT);
  auto error = jocky_rt_last_error(context);
  EXPECT_EQ(std::string(error.code, error.code_size), "OPCODE_NOT_ALLOWED");
  char hash[65]{};
  EXPECT_EQ(jocky_rt_fixture_semantic_hash(context, hash, sizeof(hash)), JOCKY_OK);
  EXPECT_EQ(std::string(hash).size(), 64u);
  jocky_rt_context_destroy(context);
}
