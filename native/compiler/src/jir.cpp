#include "jocky/jir.h"

namespace jocky {
llvm::json::Array string_array(const std::set<std::string> &values) {
  llvm::json::Array out;
  for (const auto &value : values)
    out.push_back(value);
  return out;
}
llvm::json::Array string_array(const std::vector<std::string> &values) {
  llvm::json::Array out;
  for (const auto &value : values)
    out.push_back(value);
  return out;
}
void validate_jir(const FrontendModule &module) {
  int64_t next = 0, last_effect = -1;
  for (const auto &i : module.instructions) {
    auto spec = opcodes().find(i.opcode);
    if (i.id != next++ || spec == opcodes().end() || i.result_type.kind == TypeKind::Invalid)
      fail("E250", "Invalid typed JIR instruction.", i.span);
    if (i.inputs.size() < spec->second.min_inputs || i.inputs.size() > spec->second.max_inputs)
      fail("E250", "JIR operand arity does not match opcode registry.", i.span);
    for (auto input : i.inputs)
      if (input < 0 || input >= i.id)
        fail("E250", "JIR operand is not an earlier SSA value.", i.span);
    if (i.span.start.line < 1 || i.span.start.column < 1 ||
        i.span.end.offset < i.span.start.offset || i.span.end.line < i.span.start.line ||
        (i.span.end.line == i.span.start.line && i.span.end.column < i.span.start.column))
      fail("E250", "Invalid JIR source span.", i.span);
    if (i.opcode != "BIND" && i.result_type.kind != TypeKind::Dataset)
      fail("E250", "Opcode requires a dataset result.", i.span);
    if (spec->second.effect == "read") {
      auto name = i.attributes.getString("collector");
      if (!name || !collectors().contains(name->str()))
        fail("E250", "Read instruction has no registered collector.", i.span);
      const auto &collector = collectors().at(name->str());
      if (collector.opcode != i.opcode || collector.domain != i.result_type.domain ||
          i.required_capabilities.empty())
        fail("E250", "Read instruction disagrees with collector schema or capability contract.",
             i.span);
      for (const auto &[field, type] : i.result_type.fields)
        if (field_type(dataset(collector.domain), field, i.span) != type)
          fail("E250", "Invalid collector field type.", i.span);
    }
    const std::set<std::string> row_operations{
        "FILTER", "EVENT_FILTER", "EVENT_NORMALIZE", "PROJECT", "SORT",
        "LIMIT",  "GROUP",        "CORRELATE",       "JOIN",    "DRIVER_RISK_LOOKUP"};
    if (row_operations.contains(i.opcode)) {
      if (module.instructions.at(i.inputs.front()).result_type.kind != TypeKind::Dataset)
        fail("E250", "Dataset operation received a scalar operand.", i.span);
      const auto &input_type = module.instructions.at(i.inputs.front()).result_type;
      if ((i.opcode == "FILTER" || i.opcode == "EVENT_FILTER" || i.opcode == "EVENT_NORMALIZE" ||
           i.opcode == "SORT" || i.opcode == "LIMIT") &&
          input_type != i.result_type)
        fail("E250", "Row-preserving operation changed its schema.", i.span);
      if (i.opcode == "PROJECT")
        for (const auto &[field, type] : i.result_type.fields)
          if (field_type(input_type, field, i.span) != type)
            fail("E250", "Projection changed a field type.", i.span);
      if ((i.opcode == "JOIN" || i.opcode == "CORRELATE") &&
          module.instructions.at(i.inputs[1]).result_type.kind != TypeKind::Dataset)
        fail("E250", "Correlation received a scalar operand.", i.span);
    }
    if (spec->second.effect != "pure") {
      if (i.effect_predecessor != last_effect)
        fail("E250", "Broken JIR effect ordering.", i.span);
      last_effect = i.id;
    } else if (i.effect_predecessor != -1)
      fail("E250", "Pure instruction cannot consume an effect token.", i.span);
    for (const auto &cap : i.required_capabilities)
      if (!module.required_capabilities.contains(cap))
        fail("E250", "Instruction capability absent from module requirements.", i.span);
  }
}
llvm::json::Object jir_json(const FrontendModule &m) {
  validate_jir(m);
  llvm::json::Array instructions;
  for (const auto &i : m.instructions) {
    const auto &spec = opcodes().at(i.opcode);
    llvm::json::Array inputs;
    for (auto id : i.inputs)
      inputs.push_back(id);
    instructions.push_back(llvm::json::Object{
        {"id", i.id},
        {"opcode", i.opcode},
        {"family", spec.family},
        {"inputs", std::move(inputs)},
        {"result_type", type_json(i.result_type)},
        {"attributes", llvm::json::Object(i.attributes)},
        {"span", span_json(i.span)},
        {"required_capabilities", string_array(i.required_capabilities)},
        {"resource_class", spec.resource_class},
        {"effect", spec.effect},
        {"effect_predecessor", i.effect_predecessor < 0 ? llvm::json::Value(nullptr)
                                                        : llvm::json::Value(i.effect_predecessor)},
        {"target_os", string_array(m.target_os)}});
  }
  return llvm::json::Object{{"schema_version", "1.0.0"},
                            {"kind", "JIRModule"},
                            {"compiler_version", "0.3.0"},
                            {"source_hash", m.source_hash},
                            {"hunt", m.hunt_name},
                            {"case", m.case_name},
                            {"targets", llvm::json::Array(m.targets)},
                            {"runtime", llvm::json::Object(m.runtime)},
                            {"target_os", string_array(m.target_os)},
                            {"required_capabilities", string_array(m.required_capabilities)},
                            {"budget", llvm::json::Object(m.budget)},
                            {"instructions", std::move(instructions)},
                            {"executable", false}};
}
llvm::json::Object plan_json(const FrontendModule &m) {
  llvm::json::Array schemas, warnings, projections;
  for (const auto &i : m.instructions)
    if (auto fields = i.attributes.getArray("fields"))
      projections.push_back(
          llvm::json::Object{{"instruction_id", i.id}, {"fields", llvm::json::Array(*fields)}});
  for (const auto &i : m.instructions)
    schemas.push_back(
        llvm::json::Object{{"instruction_id", i.id}, {"result_type", type_json(i.result_type)}});
  for (const auto &w : m.warnings)
    warnings.push_back(llvm::json::Object{{"code", w.code},
                                          {"message", w.message},
                                          {"span", span_json(w.span)},
                                          {"help", w.help},
                                          {"severity", "warning"}});
  return llvm::json::Object{{"schema_version", "1.0.0"},
                            {"kind", "FrontendExecutionPlan"},
                            {"source_hash", m.source_hash},
                            {"jir_hash", sha256(canonical_json(jir_json(m)))},
                            {"targets", llvm::json::Array(m.targets)},
                            {"target_os", string_array(m.target_os)},
                            {"required_collectors", string_array(m.required_collectors)},
                            {"required_capabilities", string_array(m.required_capabilities)},
                            {"pushdown", llvm::json::Array(m.pushdown)},
                            {"projected_fields", std::move(projections)},
                            {"expected_result_schemas", std::move(schemas)},
                            {"budget", llvm::json::Object(m.budget)},
                            {"runtime", llvm::json::Object(m.runtime)},
                            {"warnings", std::move(warnings)},
                            {"dispatchable", false},
                            {"admission_status", "REQUIRES_ENDPOINT_POLICY_AND_LLVM_LOWERING"}};
}
} // namespace jocky
