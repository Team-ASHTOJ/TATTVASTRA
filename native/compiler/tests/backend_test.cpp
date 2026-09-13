#include "jocky/backend.h"
#include "jocky/parser.h"
#include "jocky/semantic.h"
#include <filesystem>
#include <fstream>
#include <gtest/gtest.h>
#include <sstream>

using namespace jocky;

namespace {
FrontendModule compile(const std::string &body) {
  auto source = "hunt \"backend\" { " + body + " }";
  auto program = Parser(lex(source)).parse();
  return SemanticAnalyzer(program, source).analyze();
}

std::string run_fixture(LoweredVariant variant, const VariantOptions &options,
                        jocky_status expected = JOCKY_OK) {
  jocky_context *runtime = nullptr;
  EXPECT_EQ(jocky_rt_fixture_context_create(&runtime), JOCKY_OK);
  if (options.protect_literals)
    EXPECT_EQ(jocky_rt_set_literal_key(runtime, options.literal_key_id.data(),
                                       options.literal_key_id.size(), options.literal_key.data(),
                                       options.literal_key.size()),
              JOCKY_OK);
  StageProfile profile;
  std::string error;
  EXPECT_EQ(execute_orc(std::move(variant), runtime, profile, error), expected) << error;
  char hash[65]{};
  EXPECT_EQ(jocky_rt_fixture_semantic_hash(runtime, hash, sizeof(hash)), JOCKY_OK);
  jocky_rt_context_destroy(runtime);
  return hash;
}
} // namespace

TEST(LLVMBackend, LowersFixedCollectorsToRuntimeAbi) {
  auto module = compile(
      "capabilities { system.read users.read process.read network.read persistence.read "
      "drivers.read logs.read filesystem.metadata filesystem.content } collect system as sys "
      "collect users as users collect processes as proc "
      "collect interfaces as nic collect connections as net collect routes as routes collect "
      "files { path path(\"/fixture/metadata\") } as files collect file_hash { path "
      "path(\"/fixture/hash\") } as digest collect services as svc collect events as events "
      "collect drivers as drivers");
  VariantOptions options;
  options.seed = 42;
  auto lowered = lower_to_llvm(module, options);
  auto ir = render_llvm_ir(lowered);
  for (const auto *symbol :
       {"jocky_rt_system_info", "jocky_rt_users", "jocky_rt_processes", "jocky_rt_interfaces",
        "jocky_rt_connections", "jocky_rt_routes", "jocky_rt_file_metadata", "jocky_rt_file_hash",
        "jocky_rt_services", "jocky_rt_events", "jocky_rt_drivers"})
    EXPECT_NE(ir.find(symbol), std::string::npos) << symbol;
  EXPECT_EQ(lowered.manifest.structural.generated_helper_count, module.instructions.size());
  EXPECT_FALSE(lowered.manifest.structural.fingerprint.empty());
  EXPECT_NE(ir.find("layout.marker"), std::string::npos);
}

TEST(LLVMBackend, SameSeedReproducesAndDifferentSeedDiversifies) {
  auto module = compile("capabilities { system.read } collect system as sys let copy = sys");
  VariantOptions options;
  options.seed = 7;
  auto first = lower_to_llvm(module, options);
  auto second = lower_to_llvm(module, options);
  EXPECT_EQ(render_llvm_ir(first), render_llvm_ir(second));
  EXPECT_EQ(first.manifest.variant_id, second.manifest.variant_id);
  EXPECT_EQ(first.manifest.structural.fingerprint, second.manifest.structural.fingerprint);

  bool structurally_distinct = false;
  for (uint64_t seed = 8; seed < 32 && !structurally_distinct; ++seed) {
    options.seed = seed;
    auto different = lower_to_llvm(module, options);
    EXPECT_NE(render_llvm_ir(first), render_llvm_ir(different));
    structurally_distinct =
        first.manifest.structural.fingerprint != different.manifest.structural.fingerprint;
  }
  EXPECT_TRUE(structurally_distinct);
}

TEST(LLVMBackend, OrcExecutesEquivalentVariantsWithoutStandaloneExecutable) {
  auto module = compile("capabilities { system.read } collect system as sys let copy = sys");
  VariantOptions first_options;
  first_options.seed = 100;
  VariantOptions second_options = first_options;
  second_options.seed = 200;
  auto first_hash = run_fixture(lower_to_llvm(module, first_options), first_options);
  auto second_hash = run_fixture(lower_to_llvm(module, second_options), second_options);
  EXPECT_EQ(first_hash, second_hash);
}

TEST(LLVMBackend, TargetMachineEmitsActualDistinctObjects) {
  auto module = compile("capabilities { system.read } collect system as sys");
  VariantOptions first_options;
  first_options.seed = 1;
  VariantOptions second_options = first_options;
  second_options.seed = 2;
  auto first = lower_to_llvm(module, first_options);
  auto second = lower_to_llvm(module, second_options);
  auto directory = std::filesystem::temp_directory_path();
  auto first_path = directory / (first.manifest.variant_id + ".jocky-test.o");
  auto second_path = directory / (second.manifest.variant_id + ".jocky-test.o");
  emit_aot_object(first, first_path.string());
  emit_aot_object(second, second_path.string());
  EXPECT_GT(std::filesystem::file_size(first_path), 0u);
  EXPECT_GT(std::filesystem::file_size(second_path), 0u);
  EXPECT_NE(first.manifest.artifact_hash, second.manifest.artifact_hash);
  std::filesystem::remove(first_path);
  std::filesystem::remove(second_path);
}

TEST(LiteralPool, AesGcmHidesPlaintextAndRejectsTampering) {
  const std::string marker = "jocky-sensitive-fixture-marker";
  auto module = compile("capabilities { filesystem.metadata } collect files { path path(\"" +
                        marker + "\") } as files");
  VariantOptions options;
  options.seed = 99;
  options.protect_literals = true;
  options.literal_key.assign(32, 0x5a);
  options.literal_key_id = "ephemeral-test-key";
  auto protected_variant = lower_to_llvm(module, options);
  EXPECT_EQ(render_llvm_ir(protected_variant).find(marker), std::string::npos);
  EXPECT_TRUE(protected_variant.manifest.literal_pool.has_value());
  auto artifact = std::filesystem::temp_directory_path() /
                  (protected_variant.manifest.variant_id + ".protected-test.o");
  emit_aot_object(protected_variant, artifact.string());
  std::ifstream artifact_input(artifact, std::ios::binary);
  std::ostringstream artifact_bytes;
  artifact_bytes << artifact_input.rdbuf();
  EXPECT_EQ(artifact_bytes.str().find(marker), std::string::npos);
  std::filesystem::remove(artifact);
  EXPECT_FALSE(run_fixture(std::move(protected_variant), options).empty());

  auto wrong_key_variant = lower_to_llvm(module, options);
  auto wrong_key = options;
  wrong_key.literal_key.assign(32, 0x6b);
  (void)run_fixture(std::move(wrong_key_variant), wrong_key, JOCKY_DENIED);

  auto tampered = lower_to_llvm(module, options);
  auto pool = *tampered.manifest.literal_pool;
  pool.ciphertext.front() ^= 1;
  jocky_context *runtime = nullptr;
  ASSERT_EQ(jocky_rt_fixture_context_create(&runtime), JOCKY_OK);
  ASSERT_EQ(jocky_rt_set_literal_key(runtime, options.literal_key_id.data(),
                                     options.literal_key_id.size(), options.literal_key.data(),
                                     options.literal_key.size()),
            JOCKY_OK);
  ASSERT_EQ(jocky_rt_register_literal_pool(
                runtime, pool.key_id.data(), pool.key_id.size(), pool.nonce.data(),
                pool.nonce.size(), pool.tag.data(), pool.tag.size(), pool.ciphertext.data(),
                pool.ciphertext.size(),
                reinterpret_cast<const uint8_t *>(pool.associated_data.data()),
                pool.associated_data.size()),
            JOCKY_OK);
  jocky_dataset_handle handle = 0;
  EXPECT_EQ(jocky_rt_file_metadata(runtime, 0, nullptr, 0, &handle), JOCKY_DENIED);
  auto error = jocky_rt_last_error(runtime);
  EXPECT_EQ(std::string(error.code, error.code_size), "LITERAL_AUTHENTICATION_FAILED");
  jocky_rt_context_destroy(runtime);
}
