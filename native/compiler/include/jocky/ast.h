#pragma once
#include "jocky/source.h"
#include <map>
#include <memory>

namespace jocky {
struct Expr {
  enum class Kind { Literal, Name, Call, Unary, Binary } kind;
  std::string value;
  std::string literal_kind;
  Span span;
  std::vector<std::shared_ptr<Expr>> children;
  unsigned height = 1;
};
using ExprPtr = std::shared_ptr<Expr>;
struct Option {
  std::string name;
  ExprPtr value;
  std::vector<std::string> fields;
  Span span;
};
struct PipelineOp {
  std::string kind;
  ExprPtr expression;
  std::vector<std::string> fields;
  std::string direction = "asc";
  Span span;
};
struct Statement {
  enum class Kind { Collect, Let, Correlate, Finding, Timeline, Report, Analyze, PythonCall } kind;
  std::string name;
  std::string collector;
  std::vector<Option> options;
  ExprPtr expression;
  ExprPtr right;
  std::vector<PipelineOp> pipeline;
  std::vector<std::string> sources;
  std::string severity;
  std::string format = "json";
  bool integrity = true;
  std::vector<Statement> children;
  Span span;
};
struct Selector {
  std::string kind;
  std::string value;
  Span span;
};
struct Program {
  std::string case_name;
  std::string hunt_name;
  Span span;
  std::vector<Selector> selectors;
  std::vector<std::string> target_os;
  std::map<std::string, Option> runtime;
  std::map<std::string, Option> variant;
  std::map<std::string, Option> budgets;
  std::vector<std::string> capabilities;
  std::map<std::string, std::string> python_imports;
  std::vector<Statement> statements;
};
llvm::json::Object expression_json(const ExprPtr &expression);
llvm::json::Object ast_json(const Program &program);
} // namespace jocky
