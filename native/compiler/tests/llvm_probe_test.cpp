#include "jocky/llvm_probe.h"
#include <gtest/gtest.h>

TEST(LLVMToolchain, EmitsAndExecutesRealOrcMachineCode) {
  std::string error;
  EXPECT_TRUE(jocky::verify_orc_toolchain(error)) << error;
}
