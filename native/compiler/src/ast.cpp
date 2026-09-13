#include "jocky/ast.h"

namespace jocky {
llvm::json::Object expression_json(const ExprPtr &e) {
  if (!e)
    return {};
  static const char *names[] = {"literal", "name", "call", "unary", "binary"};
  llvm::json::Array children;
  for (const auto &child : e->children)
    children.push_back(expression_json(child));
  return llvm::json::Object{{"kind", names[static_cast<int>(e->kind)]},
                            {"value", e->value},
                            {"literal_kind", e->literal_kind},
                            {"span", span_json(e->span)},
                            {"children", std::move(children)}};
}
static llvm::json::Array strings(const std::vector<std::string> &values) {
  llvm::json::Array out;
  for (const auto &v : values)
    out.push_back(v);
  return out;
}
static llvm::json::Object option_json(const Option &o) {
  return llvm::json::Object{{"name", o.name},
                            {"value", expression_json(o.value)},
                            {"fields", strings(o.fields)},
                            {"span", span_json(o.span)}};
}
static llvm::json::Object statement_json(const Statement &s) {
  static const char *names[] = {"collect",  "let",    "correlate", "finding",
                                "timeline", "report", "analyze"};
  llvm::json::Array options, pipeline, children;
  for (const auto &o : s.options)
    options.push_back(option_json(o));
  for (const auto &op : s.pipeline)
    pipeline.push_back(llvm::json::Object{{"kind", op.kind},
                                          {"expression", expression_json(op.expression)},
                                          {"fields", strings(op.fields)},
                                          {"direction", op.direction},
                                          {"span", span_json(op.span)}});
  for (const auto &child : s.children)
    children.push_back(statement_json(child));
  return llvm::json::Object{{"kind", names[static_cast<int>(s.kind)]},
                            {"name", s.name},
                            {"collector", s.collector},
                            {"options", std::move(options)},
                            {"expression", expression_json(s.expression)},
                            {"right", expression_json(s.right)},
                            {"pipeline", std::move(pipeline)},
                            {"sources", strings(s.sources)},
                            {"severity", s.severity},
                            {"format", s.format},
                            {"integrity", s.integrity},
                            {"children", std::move(children)},
                            {"span", span_json(s.span)}};
}
llvm::json::Object ast_json(const Program &p) {
  llvm::json::Array selectors, statements;
  llvm::json::Object runtime, variant, budget;
  for (const auto &s : p.selectors)
    selectors.push_back(
        llvm::json::Object{{"kind", s.kind}, {"value", s.value}, {"span", span_json(s.span)}});
  for (const auto &[key, o] : p.runtime)
    runtime[key] = option_json(o);
  for (const auto &[key, o] : p.variant)
    variant[key] = option_json(o);
  for (const auto &[key, o] : p.budgets)
    budget[key] = option_json(o);
  for (const auto &s : p.statements)
    statements.push_back(statement_json(s));
  return llvm::json::Object{{"schema_version", "1.0.0"},
                            {"kind", "Program"},
                            {"case", p.case_name},
                            {"hunt", p.hunt_name},
                            {"span", span_json(p.span)},
                            {"selectors", std::move(selectors)},
                            {"target_os", strings(p.target_os)},
                            {"runtime", std::move(runtime)},
                            {"variant", std::move(variant)},
                            {"budget", std::move(budget)},
                            {"capabilities", strings(p.capabilities)},
                            {"statements", std::move(statements)}};
}
} // namespace jocky
