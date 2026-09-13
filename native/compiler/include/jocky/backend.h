#pragma once

#include "jocky/jir.h"
#include "jocky/literal_pool.h"
#include "jocky/runtime.h"
#include <llvm/IR/LLVMContext.h>
#include <llvm/IR/Module.h>
#include <memory>
#include <optional>

namespace jocky {
inline constexpr const char *compiler_version = "0.3.0";

struct StageProfile {
  std::optional<double> lex_ms;
  std::optional<double> parse_ms;
  std::optional<double> semantic_ms;
  std::optional<double> jir_ms;
  std::optional<double> variant_ms;
  std::optional<double> llvm_generation_ms;
  std::optional<double> optimization_ms;
  std::optional<double> aot_ms;
  std::optional<double> jit_compile_ms;
  std::optional<double> execution_ms;
};

struct StructuralMetrics {
  uint64_t basic_block_count = 0;
  uint64_t function_count = 0;
  uint64_t generated_helper_count = 0;
  std::vector<uint32_t> lowering_strategy_ids;
  std::string fingerprint;
};

struct VariantOptions {
  uint64_t seed = 0;
  std::string profile = "balanced";
  std::string execution_mode = "memory";
  bool protect_literals = false;
  std::vector<uint8_t> literal_key;
  std::string literal_key_id;
};

struct VariantManifest {
  std::string variant_id;
  std::string variant_seed;
  std::string source_hash;
  std::string jir_hash;
  std::string llvm_ir_hash;
  std::string llvm_version;
  std::string target_triple;
  std::string execution_mode;
  std::string profile;
  std::optional<std::string> artifact_hash;
  std::optional<std::string> semantic_result_hash;
  StructuralMetrics structural;
  std::optional<ProtectedLiteralPool> literal_pool;
  std::string created_at;
};

struct LoweredVariant {
  std::unique_ptr<llvm::LLVMContext> context;
  std::unique_ptr<llvm::Module> module;
  VariantManifest manifest;
  StageProfile profile;
  std::string entry_symbol;
};

LoweredVariant lower_to_llvm(const FrontendModule &module, const VariantOptions &options);
std::string render_llvm_ir(const LoweredVariant &variant);
void emit_aot_object(LoweredVariant &variant, const std::string &path);
jocky_status execute_orc(LoweredVariant &&variant, jocky_context *runtime, StageProfile &profile,
                         std::string &error);
llvm::json::Object profile_json(const StageProfile &profile);
llvm::json::Object manifest_json(const VariantManifest &manifest);
std::string manifest_summary(const VariantManifest &manifest);
void write_manifest(const VariantManifest &manifest, const std::string &path);
VariantManifest read_manifest(const std::string &path);
std::string utc_now();
} // namespace jocky
