#include "jocky/semantic.h"

namespace jocky {
TypedExpression SemanticAnalyzer::infer(const ExprPtr &e, const Type *row,
                                        const std::string &row_name, int64_t row_id) {
  TypedExpression result;
  result.value = expression_json(e);
  if (e->kind == Expr::Kind::Literal)
    result.type = literal_type(*e);
  else if (e->kind == Expr::Kind::Name) {
    auto split = e->value.find('.');
    auto head = e->value.substr(0, split);
    if (row != nullptr &&
        ((split == std::string::npos && row->fields.contains(head)) || head == row_name ||
         row->fields.contains(head) || row->fields.contains(e->value))) {
      auto path =
          head == row_name && split != std::string::npos ? e->value.substr(split + 1) : e->value;
      result.type = field_type(*row, path, e->span);
      result.value["field"] = path;
      result.value["row_id"] = row_id;
    } else {
      if (row != nullptr && !bindings_.contains(head))
        field_type(*row, e->value, e->span);
      auto binding = lookup(head, e->span);
      if (split != std::string::npos) {
        if (row != nullptr)
          fail("E214", "Cross-dataset row reference requires an explicit correlation.", e->span);
        fail("E224", "Dataset fields require a row context; use where or an aggregate.", e->span);
      }
      result.type = binding.type;
      result.inputs.insert(binding.id);
      result.value["binding_id"] = binding.id;
    }
  } else if (e->kind == Expr::Kind::Call) {
    if (e->children.size() != 1)
      fail("E226", "Function requires exactly one argument.", e->span);
    auto arg = infer(e->children[0], row, row_name, row_id);
    if (e->value == "count") {
      if (arg.type.kind != TypeKind::Dataset)
        fail("E224", "count expects Dataset<T>.", e->span);
      result.type = scalar(TypeKind::Int);
    } else {
      static const std::map<std::string, TypeKind> constructors = {
          {"pid", TypeKind::Pid},    {"path", TypeKind::Path},         {"ip", TypeKind::IP},
          {"time", TypeKind::Time},  {"duration", TypeKind::Duration}, {"hash", TypeKind::Hash},
          {"bytes", TypeKind::Bytes}};
      auto constructor = constructors.find(e->value);
      if (constructor == constructors.end())
        fail("E226", "Unknown function `" + e->value + "`.", e->span);
      validate_constructor(e->value, *e->children[0], e->span);
      result.type = scalar(constructor->second);
    }
    result.inputs = arg.inputs;
    llvm::json::Array children;
    children.push_back(std::move(arg.value));
    result.value["children"] = std::move(children);
  } else {
    auto left = infer(e->children[0], row, row_name, row_id);
    result.inputs = left.inputs;
    llvm::json::Array children;
    if (e->kind == Expr::Kind::Unary) {
      if ((e->value == "not" && left.type.kind != TypeKind::Bool) ||
          (e->value == "-" && !numeric(left.type)))
        fail("E221", "Invalid unary operand type.", e->span);
      result.type = left.type;
      if (e->value == "-")
        result.value["arithmetic_policy"] = "CHECKED_OVERFLOW_AND_DIVISION";
    } else {
      auto right = infer(e->children[1], row, row_name, row_id);
      result.inputs.insert(right.inputs.begin(), right.inputs.end());
      const auto &op = e->value;
      if (op == "and" || op == "or") {
        if (left.type.kind != TypeKind::Bool || right.type.kind != TypeKind::Bool)
          fail("E221", "Boolean operators require bool operands.", e->span);
        result.type = scalar(TypeKind::Bool, left.type.nullable || right.type.nullable);
      } else if (op == "+" || op == "-" || op == "*" || op == "/") {
        if (!numeric(left.type) || !numeric(right.type))
          fail("E221", "Arithmetic requires int/float operands.", e->span);
        if (op == "/" && e->children[1]->kind == Expr::Kind::Literal &&
            std::stod(e->children[1]->value) == 0)
          fail("E225", "Division by zero.", e->span);
        result.type = scalar(left.type.kind == TypeKind::Float || right.type.kind == TypeKind::Float
                                 ? TypeKind::Float
                                 : TypeKind::Int,
                             left.type.nullable || right.type.nullable);
        result.value["arithmetic_policy"] = "CHECKED_OVERFLOW_AND_DIVISION";
      } else {
        if (!comparable(left.type, right.type, op != "==" && op != "!="))
          fail("E221",
               "Cannot compare `" + type_name(left.type) + "` with `" + type_name(right.type) +
                   "`.",
               e->span, "Use compatible types or an explicit typed literal constructor.");
        result.type = scalar(TypeKind::Bool, left.type.nullable || right.type.nullable);
      }
      children.push_back(std::move(left.value));
      children.push_back(std::move(right.value));
    }
    if (e->kind == Expr::Kind::Unary)
      children.push_back(std::move(left.value));
    result.value["children"] = std::move(children);
  }
  result.value["type"] = type_json(result.type);
  return result;
}
} // namespace jocky
