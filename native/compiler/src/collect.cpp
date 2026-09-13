#include "jocky/query.h"
#include "jocky/semantic.h"
#include <algorithm>

namespace jocky {
void SemanticAnalyzer::collect(const Statement &s) {
  auto entry = collectors().find(s.collector);
  if (entry == collectors().end())
    fail("E210", "Unknown collector `" + s.collector + "`.", s.span,
         "Use a collector listed in docs/LANGUAGE_SPEC.md.");
  const auto &spec = entry->second;
  Type type = dataset(spec.domain);
  std::map<std::string, const Option *> options;
  for (const auto &option : s.options) {
    if (!spec.options.contains(option.name))
      fail("E230", "Unsupported option `" + option.name + "` for `" + s.collector + "`.",
           option.span);
    if (!options.emplace(option.name, &option).second)
      fail("E123", "Duplicate collector option.", option.span);
  }
  if (spec.path_required && !options.contains("path"))
    fail("E230", "Collector requires an explicit path scope.", s.span,
         "Add path path(\"approved-path\") to the option block.");
  if (options.contains("fields"))
    type = project_type(type, options.at("fields")->fields, options.at("fields")->span);
  else
    for (const auto &field : spec.omitted_by_default)
      type.fields.erase(field);
  std::set<std::string> caps{require(spec.capability, s.span, s.collector)};
  if (type.fields.contains("sha256") || s.collector == "process_hash" ||
      s.collector == "driver_hash" || s.collector == "file_content")
    caps.insert(require("filesystem.content", s.span, s.collector));
  llvm::json::Object attributes{{"collector", s.collector},
                                {"binding", s.name},
                                {"availability", "REQUIRES_ENDPOINT_ADAPTER"},
                                {"provenance", "PRESERVE_OBSERVATION_ENVELOPE"}};
  llvm::json::Object typed_options;
  for (const auto &[name, option] : options) {
    if (name == "fields" || name == "where" || name == "limit")
      continue;
    auto value = infer(option->value);
    TypeKind expected = TypeKind::String;
    if (name == "pid")
      expected = TypeKind::Pid;
    if (name == "path")
      expected = TypeKind::Path;
    if (name == "recursive")
      expected = TypeKind::Bool;
    if (name == "since" || name == "until")
      expected = TypeKind::Time;
    if (value.type.kind != expected || value.type.nullable || !value.inputs.empty())
      fail("E230", "Option `" + name + "` requires a constant " + type_name(scalar(expected)) + ".",
           option->span, "Use a typed literal constructor where appropriate.");
    if (name == "protocol" && option->value->value != "tcp" && option->value->value != "udp")
      fail("E230", "protocol must be \"tcp\" or \"udp\".", option->span);
    typed_options[name] = std::move(value.value);
  }
  attributes["options"] = std::move(typed_options);
  llvm::json::Array requested_fields;
  for (const auto &[name, field] : type.fields)
    requested_fields.push_back(name);
  attributes["fields"] = std::move(requested_fields);
  module_.required_collectors.insert(s.collector);
  auto id = emit(spec.opcode, type, {}, std::move(attributes), s.span, {caps.begin(), caps.end()});
  if (type.domain == "Event")
    id = emit("EVENT_NORMALIZE", type, {id},
              llvm::json::Object{{"clock_policy", "PRESERVE_SOURCE_AND_COLLECTION_TIME"}}, s.span);
  if (options.contains("where")) {
    const auto &option = *options.at("where");
    auto predicate = infer(option.value, &type, s.name, id);
    if (predicate.type.kind != TypeKind::Bool)
      fail("E222", "where requires a bool predicate.", option.span);
    auto input = id;
    std::vector<int64_t> inputs{input};
    for (auto dependency : predicate.inputs)
      if (dependency != input)
        inputs.push_back(dependency);
    llvm::json::Object attrs{{"predicate", std::move(predicate.value)},
                             {"null_policy", "KEEP_TRUE_ONLY"}};
    id = emit(type.domain == "Event" ? "EVENT_FILTER" : "FILTER", type, inputs, attrs, option.span);
    if (predicate.inputs.empty())
      pushdown_candidate(module_, input, id, "filter", std::move(attrs));
  }
  if (options.contains("limit")) {
    auto option = options.at("limit");
    auto amount = limit_value(option->value, option->span);
    id = emit("LIMIT", type, {id}, llvm::json::Object{{"count", amount}}, option->span);
  }
  bind(s.name, type, id, s.span);
}
} // namespace jocky
