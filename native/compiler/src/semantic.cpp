#include "jocky/semantic.h"
#include <algorithm>

namespace jocky {
static std::size_t schema_size(const Type &type, unsigned depth, Span span) {
  if (depth > 16)
    fail("E250", "Nested record depth exceeds 16.", span);
  std::size_t size = 1;
  for (const auto &[name, field] : type.fields) {
    size += schema_size(field, depth + 1, span);
    if (size > 1024)
      fail("E250", "Result schema exceeds 1024 type nodes.", span);
  }
  return size;
}
Binding SemanticAnalyzer::lookup(const std::string &name, Span span) const {
  auto found = bindings_.find(name);
  if (found == bindings_.end())
    fail("E211", "Undefined variable `" + name + "`.", span,
         "Declare it with collect or let before use.");
  return found->second;
}
void SemanticAnalyzer::bind(const std::string &name, Type type, int64_t id, Span span) {
  if (bindings_.contains(name))
    fail("E212", "Duplicate binding `" + name + "`.", span, "Use a new binding name.");
  bindings_.emplace(name, Binding{std::move(type), id});
}
std::string SemanticAnalyzer::require(const std::string &cap, Span span,
                                      const std::string &collector) {
  auto declared = [&](const std::string &c) {
    return std::find(program_.capabilities.begin(), program_.capabilities.end(), c) !=
           program_.capabilities.end();
  };
  std::string effective = cap;
  if (!declared(cap) && cap == "filesystem.content" && declared("filesystem.read"))
    effective = "filesystem.read";
  if (!declared(cap) && cap == "persistence.read" && collector == "services" &&
      declared("services.read"))
    effective = "services.read";
  if (!declared(effective))
    fail("E241", "Collector `" + collector + "` requires capability `" + cap + "`.", span,
         "Add " + cap + " to capabilities; endpoint policy must still authorize it.");
  module_.required_capabilities.insert(effective);
  if (effective != cap)
    module_.warnings.push_back(
        {"W241", "Legacy capability `" + effective + "` used for `" + collector + "`.", span,
         "Prefer " + cap + ".", "warning"});
  return effective;
}
int64_t SemanticAnalyzer::emit(const std::string &opcode, Type type, std::vector<int64_t> inputs,
                               llvm::json::Object attrs, Span span, std::vector<std::string> caps) {
  if (module_.instructions.size() >= 65536)
    fail("E250", "JIR instruction limit exceeded.", span);
  schema_nodes_ += schema_size(type, 0, span);
  if (schema_nodes_ > 65536)
    fail("E250", "Module exceeds 65536 result type nodes.", span);
  auto id = static_cast<int64_t>(module_.instructions.size());
  auto predecessor = opcodes().at(opcode).effect == "pure" ? -1 : last_effect_;
  if (opcodes().at(opcode).effect != "pure")
    last_effect_ = id;
  module_.instructions.push_back({id, opcode, std::move(inputs), std::move(type), std::move(attrs),
                                  span, std::move(caps), predecessor});
  return id;
}
void SemanticAnalyzer::statement(const Statement &s) {
  if (reported_)
    fail("E239", "Report export must be the final statement.", s.span);
  switch (s.kind) {
  case Statement::Kind::Collect:
    collect(s);
    break;
  case Statement::Kind::Let:
    let(s);
    break;
  default:
    investigate(s);
    break;
  }
}
FrontendModule SemanticAnalyzer::analyze() {
  configuration();
  for (const auto &s : program_.statements)
    statement(s);
  for (const auto &cap : program_.capabilities)
    if (!module_.required_capabilities.contains(cap))
      module_.warnings.push_back({"W240",
                                  "Declared capability `" + cap + "` is not required by this hunt.",
                                  program_.span, "Remove unused grants when possible.", "warning"});
  validate_jir(module_);
  return std::move(module_);
}
} // namespace jocky
