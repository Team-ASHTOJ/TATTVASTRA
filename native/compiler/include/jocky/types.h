#pragma once
#include "jocky/ast.h"
#include <set>

namespace jocky {
enum class TypeKind {
  Invalid,
  Int,
  Float,
  Bool,
  String,
  Time,
  Duration,
  Hash,
  IP,
  Path,
  Pid,
  Bytes,
  Dataset,
  Record
};
struct Type {
  TypeKind kind = TypeKind::Invalid;
  bool nullable = false;
  std::string domain;
  std::map<std::string, Type> fields;
  bool operator==(const Type &) const = default;
};
Type scalar(TypeKind kind, bool nullable = false);
Type dataset(const std::string &domain);
std::string type_name(const Type &type);
llvm::json::Object type_json(const Type &type);
Type field_type(const Type &row, const std::string &path, Span span);
bool numeric(const Type &type);
bool comparable(const Type &a, const Type &b, bool ordering);
int64_t quantity(const std::string &text, const std::string &unit_class, Span span);
Type literal_type(const Expr &expression);
void validate_constructor(const std::string &name, const Expr &argument, Span span);

struct CollectorSpec {
  std::string opcode;
  std::string domain;
  std::string capability;
  std::set<std::string> options;
  std::set<std::string> omitted_by_default;
  bool path_required = false;
};
struct OpcodeSpec {
  std::string family;
  std::string effect;
  std::string resource_class;
  std::size_t min_inputs;
  std::size_t max_inputs;
};
const std::map<std::string, CollectorSpec> &collectors();
const std::map<std::string, OpcodeSpec> &opcodes();
const std::set<std::string> &capability_names();
} // namespace jocky
