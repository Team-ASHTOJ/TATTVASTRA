#include "jocky/query.h"
#include "jocky/semantic.h"
#include <charconv>

namespace jocky {
Type project_type(const Type &input, const std::vector<std::string> &fields, Span span) {
  if (input.kind != TypeKind::Dataset)
    fail("E223", "Projection requires Dataset<T>.", span);
  if (fields.empty())
    fail("E223", "Field list must not be empty.", span);
  Type result = input;
  result.fields.clear();
  for (const auto &field : fields) {
    if (!result.fields.emplace(field, field_type(input, field, span)).second)
      fail("E223", "Duplicate field `" + field + "`.", span);
  }
  return result;
}
int64_t limit_value(const ExprPtr &e, Span span) {
  if (e->kind != Expr::Kind::Literal || literal_type(*e).kind != TypeKind::Int)
    fail("E223", "limit requires an integer literal.", span);
  int64_t value = 0;
  std::from_chars(e->value.data(), e->value.data() + e->value.size(), value);
  if (value < 1 || value > 1000000)
    fail("E223", "limit must be between 1 and 1000000.", span);
  return value;
}
void pushdown_candidate(FrontendModule &m, int64_t input, int64_t branch, const std::string &kind,
                        llvm::json::Object attrs) {
  auto cursor = input;
  while (cursor >= 0) {
    const auto &i = m.instructions.at(static_cast<std::size_t>(cursor));
    if (opcodes().at(i.opcode).effect == "read") {
      m.pushdown.push_back(llvm::json::Object{
          {"collector_instruction_id", cursor},
          {"branch_instruction_id", branch},
          {"kind", kind},
          {"scope", "BRANCH_LOCAL"},
          {"applied", false},
          {"attributes", std::move(attrs)},
          {"condition", "REQUIRES_ADAPTER_SUPPORT_AND_BRANCH_DEPENDENCY_PRESERVATION"}});
      return;
    }
    if ((i.opcode != "BIND" && i.opcode != "FILTER" && i.opcode != "PROJECT" &&
         i.opcode != "EVENT_FILTER" && i.opcode != "EVENT_NORMALIZE") ||
        i.inputs.size() != 1)
      return;
    cursor = i.inputs.front();
  }
}
void SemanticAnalyzer::let(const Statement &s) {
  auto expression = infer(s.expression);
  Type type = expression.type;
  int64_t id;
  if (type.kind == TypeKind::Dataset && s.expression->kind == Expr::Kind::Name)
    id = lookup(s.expression->value, s.span).id;
  else
    id = emit("BIND", type, {expression.inputs.begin(), expression.inputs.end()},
              llvm::json::Object{{"value", std::move(expression.value)}}, s.expression->span);
  for (const auto &op : s.pipeline) {
    if (type.kind != TypeKind::Dataset)
      fail("E223", "Pipeline operators require Dataset<T>.", op.span);
    auto input = id;
    if (op.kind == "where") {
      auto predicate = infer(op.expression, &type, s.expression->value, id);
      if (predicate.type.kind != TypeKind::Bool)
        fail("E222", "where requires a bool predicate.", op.span);
      std::vector<int64_t> inputs{input};
      for (auto dependency : predicate.inputs)
        if (dependency != input)
          inputs.push_back(dependency);
      llvm::json::Object attrs{{"predicate", std::move(predicate.value)},
                               {"null_policy", "KEEP_TRUE_ONLY"}};
      id = emit("FILTER", type, inputs, attrs, op.span);
      if (predicate.inputs.empty())
        pushdown_candidate(module_, input, id, "filter", std::move(attrs));
    } else if (op.kind == "select") {
      type = project_type(type, op.fields, op.span);
      llvm::json::Object attrs{{"fields", string_array(op.fields)},
                               {"provenance", "PRESERVE_OBSERVATION_ENVELOPE"}};
      id = emit("PROJECT", type, {input}, attrs, op.span);
      pushdown_candidate(module_, input, id, "project", std::move(attrs));
    } else if (op.kind == "sort") {
      auto field = field_type(type, op.fields.front(), op.span);
      if (field.kind == TypeKind::Record || field.kind == TypeKind::Dataset)
        fail("E223", "sort requires a scalar field.", op.span);
      id = emit("SORT", type, {input},
                llvm::json::Object{{"field", op.fields.front()},
                                   {"direction", op.direction},
                                   {"nulls", "last"},
                                   {"stable", true}},
                op.span);
    } else if (op.kind == "limit")
      id = emit("LIMIT", type, {input},
                llvm::json::Object{{"count", limit_value(op.expression, op.span)}}, op.span);
    else if (op.kind == "group") {
      type = project_type(type, op.fields, op.span);
      for (const auto &[name, field] : type.fields)
        if (field.kind == TypeKind::Record)
          fail("E223", "Grouping keys must be scalar.", op.span);
      if (type.fields.contains("count"))
        fail("E223", "Grouping key conflicts with aggregate field count.", op.span);
      type.domain = "Group";
      type.fields.emplace("count", scalar(TypeKind::Int));
      id = emit("GROUP", type, {input},
                llvm::json::Object{{"keys", string_array(op.fields)},
                                   {"aggregate", "count"},
                                   {"null_policy", "GROUP_NULLS_TOGETHER"}},
                op.span);
    }
  }
  id = emit("BIND", type, {id}, llvm::json::Object{{"binding", s.name}}, s.span);
  bind(s.name, type, id, s.span);
}
} // namespace jocky
