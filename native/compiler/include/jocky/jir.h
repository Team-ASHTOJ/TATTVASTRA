#pragma once
#include "jocky/types.h"

namespace jocky {
struct Instruction {
  int64_t id;
  std::string opcode;
  std::vector<int64_t> inputs;
  Type result_type;
  llvm::json::Object attributes;
  Span span;
  std::vector<std::string> required_capabilities;
  int64_t effect_predecessor = -1;
};
struct FrontendModule {
  std::string source_hash;
  std::string hunt_name;
  std::string case_name;
  std::vector<std::string> target_os;
  llvm::json::Array targets;
  llvm::json::Object budget;
  llvm::json::Object runtime;
  std::set<std::string> required_capabilities;
  std::set<std::string> required_collectors;
  std::vector<Instruction> instructions;
  llvm::json::Array pushdown;
  std::vector<Diagnostic> warnings;
};
llvm::json::Object jir_json(const FrontendModule &module);
llvm::json::Object plan_json(const FrontendModule &module);
void validate_jir(const FrontendModule &module);
llvm::json::Array string_array(const std::set<std::string> &values);
llvm::json::Array string_array(const std::vector<std::string> &values);
} // namespace jocky
