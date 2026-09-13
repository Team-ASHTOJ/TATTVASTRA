#include "jocky/parser.h"
#include "jocky/semantic.h"
#include <gtest/gtest.h>
#include <random>

using namespace jocky;
static Program parse(const std::string &source) { return Parser(lex(source)).parse(); }
static FrontendModule compile(const std::string &body) {
  auto source = "hunt \"test\" { " + body + " }";
  auto ast = parse(source);
  return SemanticAnalyzer(ast, source).analyze();
}
static void rejects(const std::string &body, const std::string &code) {
  try {
    compile(body);
    FAIL() << "Accepted invalid source: " << body;
  } catch (const FrontendError &e) {
    EXPECT_EQ(e.diagnostic.code, code) << e.what();
    EXPECT_GE(e.diagnostic.span.start.line, 1U);
    EXPECT_GE(e.diagnostic.span.start.column, 1U);
  }
}
TEST(Lexer, CommentsStringsAndSpans) {
  auto tokens = lex("// comment\n/* block */ hunt \"a\\n\\u03bb\" { }\n");
  ASSERT_EQ(tokens.size(), 5U);
  EXPECT_EQ(tokens[0].text, "hunt");
  EXPECT_EQ(tokens[0].span.start.line, 2U);
  EXPECT_EQ(tokens[0].span.start.column, 13U);
  EXPECT_EQ(tokens[1].value, "a\nλ");
  EXPECT_EQ(tokens.back().kind, TokenKind::End);
}
TEST(Lexer, UnterminatedAndInvalid) {
  for (const auto &source : {"/*", "\"bad", "\"\\q\"", "@", "1e+"})
    EXPECT_THROW(lex(source), FrontendError);
  EXPECT_THROW(lex(std::string(262145, ' ')), FrontendError);
  EXPECT_THROW(lex(std::string(1, static_cast<char>(0xff))), FrontendError);
}
TEST(Parser, CaseAndPrecedence) {
  auto ast = parse("case \"c\" { hunt \"h\" { let x = 1 + 2 * 3 } }");
  ASSERT_EQ(ast.statements.size(), 1U);
  EXPECT_EQ(ast.case_name, "c");
  auto expression = ast.statements[0].expression;
  EXPECT_EQ(expression->value, "+");
  EXPECT_EQ(expression->children[1]->value, "*");
}
TEST(Parser, DeterministicAst) {
  const std::string source = "hunt \"x\" { let n = (2 + 3) * 4 }";
  EXPECT_EQ(canonical_json(ast_json(parse(source))), canonical_json(ast_json(parse(source))));
}
TEST(Parser, RejectsTrailingAndDeclarationsAfterStatements) {
  rejects("let x = 1 capabilities { system.read }", "E128");
  EXPECT_THROW(parse("hunt \"a\" {} hunt \"b\" {}"), FrontendError);
  rejects("runtime { backend llvm backend llvm }", "E123");
}
TEST(Parser, BoundedExpressionTrees) {
  std::string chain = "let x = 1";
  for (int i = 0; i < 65; ++i)
    chain += " + 1";
  rejects(chain, "E122");
  rejects("let x = " + std::string(66, '(') + "1" + std::string(66, ')'), "E122");
}
TEST(Types, PrimitiveInference) {
  auto m = compile(
      "let a = -9223372036854775808 let b = 1.5 let c = true let d = \"text\" let e = "
      "time(\"2024-02-29T12:34:56Z\") let f = 5s let g = "
      "hash(\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\") let h = "
      "ip(\"2001:db8::1\") let i = path(\"C:\\\\evidence\") let j = pid(42) let k = bytes(42)");
  std::set<TypeKind> kinds;
  for (const auto &i : m.instructions)
    kinds.insert(i.result_type.kind);
  EXPECT_EQ(kinds.size(), 11U);
}
TEST(Types, InvalidLiterals) {
  rejects("let n = 9223372036854775808", "E220");
  rejects("let n = 1e999", "E220");
  rejects("let n = pid(4294967296)", "E226");
  rejects("let n = ip(\":::1\")", "E226");
  rejects("let n = time(\"2023-02-29T00:00:00Z\")", "E226");
  rejects("let n = hash(\"bad\")", "E226");
  rejects("let n = path(\"\")", "E226");
  rejects("let n = 1 / 0", "E225");
}
TEST(Types, DomainsAndNullableFields) {
  EXPECT_EQ(dataset("Process").fields.at("pid").kind, TypeKind::Pid);
  EXPECT_TRUE(dataset("Connection").fields.at("pid").nullable);
  EXPECT_TRUE(field_type(dataset("Connection"), "remote.is_public", {}).nullable);
  for (const auto &domain : {"Endpoint", "SystemInfo", "Process", "Connection", "Interface",
                             "Route", "File", "Event", "User", "Service", "Driver", "Module",
                             "Artifact", "Observation", "Finding", "TimelineEvent"})
    EXPECT_FALSE(dataset(domain).fields.empty());
}
TEST(Types, CrossDomainAndScalarComparison) {
  rejects("capabilities { process.read } collect processes as proc let x = proc | where remote == "
          "ip(\"1.2.3.4\")",
          "E213");
  rejects("let x = pid(1) == 1", "E221");
  rejects("let x = true + 1", "E221");
  EXPECT_NO_THROW(compile("let x = 1 == 1.0"));
}
TEST(Semantics, BindingsAndCount) {
  rejects("let x = absent", "E211");
  rejects("let x = 1 let x = 2", "E212");
  rejects("let x = count(1)", "E224");
  auto m = compile("capabilities { process.read } collect processes as proc let n = count(proc)");
  EXPECT_EQ(m.instructions.back().result_type.kind, TypeKind::Int);
}
TEST(Semantics, TargetOsIndependentOfHost) {
  for (const auto &os : {"windows", "linux"}) {
    auto m = compile(std::string("os ") + os +
                     " capabilities { drivers.read } collect drivers as drivers");
    ASSERT_EQ(m.target_os.size(), 1U);
    EXPECT_EQ(m.target_os.front(), os);
  }
  rejects("os macos", "E231");
  auto defaults = compile("");
  EXPECT_EQ(defaults.target_os, (std::vector<std::string>{"linux", "windows"}));
}
TEST(Semantics, BudgetRuntimeAndVariant) {
  rejects("budget { memory <= 0B }", "E232");
  rejects("budget { cpu <= 101% }", "E232");
  rejects("budget { io <= 5s }", "E232");
  rejects("runtime { backend python }", "E233");
  rejects("runtime { execution vm }", "E234");
  rejects("runtime { variant { profile stealth } }", "E235");
  auto m = compile("runtime { execution native variant { seed 0x2a enabled true profile minimal } "
                   "protect_literals true } budget { memory <= 1MiB }");
  EXPECT_EQ(m.budget.getInteger("memory_bytes"), 1048576);
  EXPECT_EQ(m.runtime.getObject("variant")->getString("seed"), "000000000000002a");
  EXPECT_TRUE(m.runtime.getBoolean("protect_literals").value_or(false));
}
TEST(Capabilities, EveryCollectorRequiresGrant) {
  for (const auto &[name, spec] : collectors()) {
    auto body = "collect " + name + (spec.path_required ? " { path path(\"/approved\") }" : "") +
                " as rows";
    rejects(body, "E241");
    EXPECT_NO_THROW(compile("capabilities { " + spec.capability +
                            (spec.capability != "filesystem.content" ? " filesystem.content" : "") +
                            " } " + body))
        << name;
  }
}
TEST(Capabilities, HashNeedsContentAndLegacyIsNarrow) {
  rejects("capabilities { process.read } collect processes { fields [pid, sha256] } as proc",
          "E241");
  EXPECT_NO_THROW(compile("capabilities { process.read filesystem.read } collect processes { "
                          "fields [pid, sha256] } as proc"));
  EXPECT_NO_THROW(compile("capabilities { services.read } collect services as svc"));
  rejects("capabilities { services.read } collect startup as items", "E241");
  rejects("capabilities { filesystem.content } collect files { path path(\"/scope\") } as items",
          "E241");
}
TEST(Queries, ProjectionAndPushdownBarriers) {
  auto m = compile(
      "capabilities { process.read } collect processes as proc let x = proc | where signed == "
      "false | select [pid, name] let y = proc | limit 10 | where signed == false | select [name]");
  ASSERT_EQ(m.pushdown.size(), 2U);
  EXPECT_FALSE(*m.pushdown[0].getAsObject()->getBoolean("applied"));
  EXPECT_EQ(m.instructions.back().result_type.fields.size(), 1U);
  EXPECT_GT(m.instructions.front().result_type.fields.size(), 1U);
  rejects("capabilities { process.read } collect processes as proc let x = proc | select [name] | "
          "where pid == pid(1)",
          "E213");
}
TEST(Queries, GroupAndScalarDependency) {
  auto m = compile("capabilities { network.read } collect connections as net let minimum = 1 let "
                   "groups = net | group by [protocol] | where count > minimum");
  EXPECT_TRUE(m.instructions.back().result_type.fields.contains("count"));
  EXPECT_EQ(m.instructions[m.instructions.size() - 2].inputs.size(), 2U);
  rejects("let x = 1 | select [name]", "E223");
}
TEST(Investigation, CorrelationTypesAndNestedProjection) {
  auto m = compile("capabilities { process.read network.read } collect processes as proc collect "
                   "connections as net correlate proc.pid with net.pid as related let names = "
                   "related | select [left.name] let x = names | where left.name == \"demo\"");
  EXPECT_TRUE(m.instructions.back().result_type.fields.contains("left.name"));
  rejects("capabilities { process.read network.read } collect processes as proc collect "
          "connections as net correlate proc.name with net.pid as bad",
          "E228");
}
TEST(Investigation, FindingDriverTimelineAndReport) {
  auto m = compile("capabilities { drivers.read } collect drivers as drivers analyze drivers { let "
                   "risky = drivers | where known_vulnerable == true finding \"risk\" { when "
                   "count(risky) > 0 severity high evidence risky } } timeline { source drivers } "
                   "report { format pdf include timeline include evidence integrity true }");
  EXPECT_EQ(m.instructions.back().opcode, "REPORT_GENERATE");
  EXPECT_EQ(m.instructions[1].attributes.get("risk_dataset")->kind(), llvm::json::Value::Null);
  rejects("report { integrity false }", "E239");
  rejects("report { include timeline }", "E239");
  rejects("capabilities { system.read } collect system as sys analyze sys", "E227");
  rejects("capabilities { system.read } collect system as sys finding \"x\" { when 1 severity high "
          "evidence sys }",
          "E229");
}
TEST(Jir, DeterminismAndEffectChain) {
  const std::string body = "capabilities { system.read process.read } collect system as sys "
                           "collect processes as proc let count_proc = count(proc) report {}";
  auto m = compile(body);
  EXPECT_EQ(canonical_json(jir_json(m)), canonical_json(jir_json(compile(body))));
  EXPECT_EQ(m.instructions[1].effect_predecessor, 0);
  EXPECT_FALSE(*jir_json(m).getBoolean("executable"));
  EXPECT_FALSE(*plan_json(m).getBoolean("dispatchable"));
  EXPECT_EQ(plan_json(m).getString("jir_hash"), sha256(canonical_json(jir_json(m))));
}
TEST(Jir, RejectsTamperedIdsOperandsAndCapabilities) {
  auto m = compile("capabilities { system.read } collect system as sys let x = sys");
  auto bad = m;
  bad.instructions[1].inputs = {99};
  EXPECT_THROW(validate_jir(bad), FrontendError);
  bad = m;
  bad.instructions[0].id = 1;
  EXPECT_THROW(validate_jir(bad), FrontendError);
  bad = m;
  bad.required_capabilities.clear();
  EXPECT_THROW(validate_jir(bad), FrontendError);
  bad = m;
  bad.instructions[0].effect_predecessor = 0;
  EXPECT_THROW(validate_jir(bad), FrontendError);
  bad = m;
  bad.instructions[0].result_type = scalar(TypeKind::Int);
  EXPECT_THROW(validate_jir(bad), FrontendError);
}
TEST(Robustness, DeterministicMalformedInputMutations) {
  std::mt19937 rng(241);
  const std::string seed = "hunt \"x\" { capabilities { process.read } collect processes { fields "
                           "[pid, name] } as proc let x = proc | where pid == pid(1) }";
  const std::string alphabet = "{}[]()\"\\\n;.*+-<>|=012abc";
  for (int iteration = 0; iteration < 500; ++iteration) {
    auto source = seed;
    for (int edit = 0; edit < 4; ++edit)
      source[rng() % source.size()] = alphabet[rng() % alphabet.size()];
    try {
      auto ast = parse(source);
      auto m = SemanticAnalyzer(ast, source).analyze();
      validate_jir(m);
    } catch (const FrontendError &e) {
      EXPECT_EQ(e.diagnostic.code.front(), 'E');
    }
  }
}
TEST(Robustness, BoundedNestedCorrelationSchemas) {
  std::string body = "capabilities { process.read } collect processes as p0 ";
  std::string key = "pid";
  for (int i = 1; i < 20; ++i) {
    auto previous = "p" + std::to_string(i - 1);
    body += "correlate " + previous + "." + key + " with " + previous + "." + key + " as p" +
            std::to_string(i) + " ";
    key = "left." + key;
  }
  rejects(body, "E250");
}
TEST(Diagnostics, StableCodeHighlightAndHelp) {
  const std::string source = "hunt \"x\" {\n  collect connections as net\n}";
  try {
    auto ast = parse(source);
    SemanticAnalyzer(ast, source).analyze();
    FAIL();
  } catch (const FrontendError &e) {
    EXPECT_EQ(e.diagnostic.code, "E241");
    EXPECT_EQ(e.diagnostic.span.start.line, 2U);
    EXPECT_EQ(e.diagnostic.span.start.column, 3U);
    auto text = render_diagnostic(e.diagnostic, source, "test.jky");
    EXPECT_NE(text.find("test.jky:2:3: JOCKY E241"), std::string::npos);
    EXPECT_NE(text.find("^^^"), std::string::npos);
    EXPECT_NE(text.find("help:"), std::string::npos);
  }
}
