#pragma once
#include "jocky/jir.h"

namespace jocky {
struct Binding {
  Type type;
  int64_t id;
};
struct TypedExpression {
  Type type;
  llvm::json::Object value;
  std::set<int64_t> inputs;
};
class SemanticAnalyzer {
  const Program &program_;
  FrontendModule module_;
  std::map<std::string, Binding> bindings_;
  std::set<std::string> finding_names_;
  int64_t last_effect_ = -1;
  int64_t timeline_ = -1;
  bool reported_ = false;
  std::size_t schema_nodes_ = 0;
  void configuration();
  void statement(const Statement &statement);
  void collect(const Statement &statement);
  void let(const Statement &statement);
  void investigate(const Statement &statement);
  std::string require(const std::string &capability, Span span, const std::string &collector);
  void bind(const std::string &name, Type type, int64_t id, Span span);
  Binding lookup(const std::string &name, Span span) const;
  TypedExpression infer(const ExprPtr &expression, const Type *row = nullptr,
                        const std::string &row_name = "", int64_t row_id = -1);
  int64_t emit(const std::string &opcode, Type type, std::vector<int64_t> inputs,
               llvm::json::Object attributes, Span span,
               std::vector<std::string> capabilities = {});

public:
  SemanticAnalyzer(const Program &program, const std::string &source) : program_(program) {
    module_.source_hash = sha256(source);
  }
  FrontendModule analyze();
};
} // namespace jocky
