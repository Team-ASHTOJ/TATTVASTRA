#include "jocky/semantic.h"

namespace jocky {
void SemanticAnalyzer::investigate(const Statement &s) {
  if (s.kind == Statement::Kind::Correlate) {
    auto key = [&](const ExprPtr &e) -> std::pair<Binding, std::string> {
      auto split = e->value.find('.');
      if (e->kind != Expr::Kind::Name || split == std::string::npos)
        fail("E228", "Correlation requires dataset.field on both sides.", e->span);
      auto value = lookup(e->value.substr(0, split), e->span);
      if (value.type.kind != TypeKind::Dataset)
        fail("E228", "Correlation operand must be a dataset.", e->span);
      return {value, e->value.substr(split + 1)};
    };
    auto [left, left_key] = key(s.expression);
    auto [right, right_key] = key(s.right);
    auto lt = field_type(left.type, left_key, s.expression->span),
         rt = field_type(right.type, right_key, s.right->span);
    if (lt.kind != rt.kind || !comparable(lt, rt, false))
      fail("E228", "Correlation keys have incompatible types.", s.span,
           "Use keys with the same scalar type.");
    Type lrecord = left.type, rrecord = right.type;
    lrecord.kind = rrecord.kind = TypeKind::Record;
    Type type{TypeKind::Dataset, false, "Correlation", {{"left", lrecord}, {"right", rrecord}}};
    auto id = emit("CORRELATE", type, {left.id, right.id},
                   llvm::json::Object{{"left_key", left_key},
                                      {"right_key", right_key},
                                      {"join_kind", "inner"},
                                      {"null_policy", "NEVER_MATCH"},
                                      {"endpoint_policy", "SAME_ENDPOINT_ONLY"},
                                      {"provenance", "RETAIN_BOTH_SOURCES"}},
                   s.span);
    bind(s.name, type, id, s.span);
    module_.warnings.push_back(
        {"W228",
         "Correlation describes a relationship, not proof of causality; PID reuse requires "
         "time-aware review.",
         s.span, "Inspect endpoint, process start times and observation times.", "warning"});
  } else if (s.kind == Statement::Kind::Finding) {
    if (s.name.empty() || !finding_names_.insert(s.name).second)
      fail("E229", "Finding title must be nonempty and unique.", s.span);
    static const std::set<std::string> severity{"info", "low", "medium", "high", "critical"};
    if (!severity.contains(s.severity))
      fail("E229", "Invalid finding severity.", s.span);
    auto condition = infer(s.expression);
    if (condition.type.kind != TypeKind::Bool)
      fail("E229", "Finding when expression must be bool.", s.expression->span,
           "Use a comparison such as count(evidence_set) > 0.");
    llvm::json::Array evidence;
    for (const auto &source : s.sources) {
      auto value = lookup(source, s.span);
      if (value.type.kind != TypeKind::Dataset)
        fail("E229", "Finding evidence must be a dataset.", s.span);
      condition.inputs.insert(value.id);
      evidence.push_back(value.id);
    }
    emit("FINDING_CREATE", dataset("Finding"), {condition.inputs.begin(), condition.inputs.end()},
         llvm::json::Object{{"title", s.name},
                            {"severity", s.severity},
                            {"condition", std::move(condition.value)},
                            {"evidence", std::move(evidence)},
                            {"null_policy", "EMIT_IF_TRUE"}},
         s.span);
  } else if (s.kind == Statement::Kind::Analyze) {
    auto value = lookup(s.sources.front(), s.span);
    if (value.type.kind != TypeKind::Dataset || value.type.domain != "Driver")
      fail("E227", "analyze requires Dataset<Driver>.", s.span);
    auto cap = require("drivers.read", s.span, "drivers");
    for (const auto &field : {"known_vulnerable", "blocklist_match"})
      value.type.fields[field] = scalar(TypeKind::Bool, true);
    for (const auto &field : {"risk", "cve", "risk_source"})
      value.type.fields[field] = scalar(TypeKind::String, true);
    auto id = emit("DRIVER_RISK_LOOKUP", value.type, {value.id},
                   llvm::json::Object{{"risk_dataset", nullptr},
                                      {"availability", "REQUIRES_SUPPLIED_RISK_DATASET"},
                                      {"missing_match_policy", "UNKNOWN"}},
                   s.span, {cap});
    if (s.name.empty())
      bindings_.at(s.sources.front()) = {value.type, id};
    else
      bind(s.name, value.type, id, s.span);
    module_.warnings.push_back(
        {"W227",
         "Driver risk analysis requires a versioned, authenticated risk dataset at execution.",
         s.span, "No risk match has been performed by this frontend.", "warning"});
    for (const auto &child : s.children) {
      if (child.kind != Statement::Kind::Let && child.kind != Statement::Kind::Finding)
        fail("E227", "analyze blocks accept let and finding statements.", child.span);
      statement(child);
    }
  } else if (s.kind == Statement::Kind::Timeline) {
    if (timeline_ >= 0 || s.sources.empty())
      fail("E238", "Use one nonempty timeline per hunt.", s.span);
    std::set<int64_t> inputs;
    for (const auto &source : s.sources) {
      auto value = lookup(source, s.span);
      if (value.type.kind != TypeKind::Dataset || !inputs.insert(value.id).second)
        fail("E238", "Timeline sources must be distinct datasets.", s.span);
    }
    timeline_ = emit("TIMELINE", dataset("TimelineEvent"), {inputs.begin(), inputs.end()},
                     llvm::json::Object{{"clock_policy", "PRESERVE_SOURCE_AND_COLLECTION_TIME"},
                                        {"missing_time_policy", "EXPLICIT_UNKNOWN"},
                                        {"provenance", "RETAIN_ALL_SOURCES"}},
                     s.span);
  } else if (s.kind == Statement::Kind::Report) {
    if ((s.format != "json" && s.format != "pdf") || !s.integrity)
      fail("E239", "Report requires format json/pdf and integrity true.", s.span);
    std::set<std::string> includes;
    for (const auto &source : s.sources) {
      if ((source != "evidence" && source != "timeline" && source != "audit") ||
          !includes.insert(source).second)
        fail("E239", "Invalid or duplicate report include.", s.span);
      if (source == "timeline" && timeline_ < 0)
        fail("E239", "Report includes a timeline that has not been defined.", s.span);
    }
    if (includes.empty())
      includes = {"evidence", "audit"};
    std::vector<int64_t> evidence;
    for (const auto &i : module_.instructions)
      if (opcodes().at(i.opcode).effect == "read" || i.opcode == "FINDING_CREATE")
        evidence.push_back(i.id);
    auto stored = emit("ARTIFACT_STORE", dataset("Artifact"), evidence,
                       llvm::json::Object{{"membership", "COLLECTIONS_AND_FINDINGS"},
                                          {"sink", "AUTHORIZED_JOB_EVIDENCE_STORE"}},
                       s.span);
    auto hashed = emit("ARTIFACT_HASH", dataset("Artifact"), {stored},
                       llvm::json::Object{{"algorithm", "sha256"}}, s.span);
    auto manifest =
        emit("MANIFEST_CREATE", dataset("Artifact"), {hashed},
             llvm::json::Object{{"producer_authentication", "REQUIRED_AT_EXECUTION"},
                                {"simulation_policy", "NO_SYNTHETIC_EVIDENCE_IN_REAL_JOBS"}},
             s.span);
    std::vector<int64_t> inputs{manifest};
    if (includes.contains("timeline"))
      inputs.push_back(timeline_);
    emit("REPORT_GENERATE", dataset("Artifact"), inputs,
         llvm::json::Object{
             {"format", s.format}, {"include", string_array(includes)}, {"integrity", true}},
         s.span);
    reported_ = true;
  }
}
} // namespace jocky
