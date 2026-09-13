#include "jocky/llvm_probe.h"
#include "jocky/parser.h"
#include "jocky/semantic.h"
#include <fstream>
#include <iostream>
#include <llvm/Config/llvm-config.h>
#include <llvm/Support/FormatVariadic.h>

int main(int argc, char **argv) {
  bool json = false;
  std::vector<std::string> args;
  for (int i = 1; i < argc; ++i) {
    if (std::string(argv[i]) == "--json")
      json = true;
    else
      args.emplace_back(argv[i]);
  }
  if (args == std::vector<std::string>{"--version"}) {
    std::cout << "jockyc 0.2.0 (typed frontend; LLVM " << LLVM_VERSION_STRING << ")\n";
    return 0;
  }
  if (args == std::vector<std::string>{"--self-test"}) {
    std::string error;
    if (!jocky::verify_orc_toolchain(error)) {
      std::cerr << "JOCKY E002: " << error << '\n';
      return 70;
    }
    std::cout << "PASS: real LLVM ORC toolchain probe (source lowering remains unavailable)\n";
    return 0;
  }
  if (args == std::vector<std::string>{"--help"}) {
    std::cout << "jockyc check|tokens|ast|jir|plan <file.jky> [--json]\n"
                 "jockyc --version | --self-test\n"
                 "Frontend output is static. Source-to-LLVM, compile, variants, run and benchmark "
                 "are unavailable.\n";
    return 0;
  }
  std::string source, filename = args.size() > 1 ? args[1] : "<command>";
  try {
    if (args.size() != 2)
      jocky::fail("E001", "Expected a command and source file; see --help.", {});
    const auto &command = args.front();
    const std::set<std::string> commands{"check", "tokens", "ast", "jir", "plan"};
    if (!commands.contains(command))
      jocky::fail("E001", "Unknown or unavailable command `" + command + "`.", {},
                  "Use --help to list implemented frontend commands.");
    std::ifstream input(filename, std::ios::binary);
    if (!input)
      jocky::fail("E003", "Cannot open source file.", {});
    source.resize(262145);
    input.read(source.data(), static_cast<std::streamsize>(source.size()));
    source.resize(static_cast<std::size_t>(input.gcount()));
    if (input.bad())
      jocky::fail("E003", "Failed to read source file.", {});
    auto tokens = jocky::lex(source);
    llvm::json::Value output = nullptr;
    if (command == "tokens")
      output = llvm::json::Object{{"schema_version", "1.0.0"},
                                  {"kind", "TokenStream"},
                                  {"tokens", jocky::tokens_json(tokens)}};
    else {
      auto program = jocky::Parser(std::move(tokens)).parse();
      if (command == "ast")
        output = jocky::ast_json(program);
      else {
        auto module = jocky::SemanticAnalyzer(program, source).analyze();
        if (command == "jir")
          output = jocky::jir_json(module);
        else if (command == "plan")
          output = jocky::plan_json(module);
        else {
          llvm::json::Array warnings;
          for (const auto &w : module.warnings)
            warnings.push_back(jocky::diagnostic_json(w, source));
          output = llvm::json::Object{
              {"schema_version", "1.0.0"},
              {"kind", "FrontendCheck"},
              {"valid", true},
              {"hunt", program.hunt_name},
              {"source_hash", module.source_hash},
              {"jir_hash", jocky::sha256(jocky::canonical_json(jocky::jir_json(module)))},
              {"instruction_count", static_cast<int64_t>(module.instructions.size())},
              {"warnings", std::move(warnings)},
              {"executable", false}};
          if (!json) {
            std::cout << "PASS: " << program.hunt_name << " — " << module.instructions.size()
                      << " typed JIR instructions\n";
            std::cout << "Static frontend validation only; source execution is unavailable.\n";
            for (const auto &w : module.warnings)
              std::cerr << jocky::render_diagnostic(w, source, filename);
            return 0;
          }
        }
      }
    }
    std::cout << (json ? jocky::canonical_json(output) : llvm::formatv("{0:2}", output).str())
              << '\n';
    return 0;
  } catch (const jocky::FrontendError &error) {
    if (json)
      std::cout << jocky::canonical_json(llvm::json::Object{
                       {"schema_version", "1.0.0"},
                       {"kind", "FrontendFailure"},
                       {"valid", false},
                       {"diagnostics",
                        llvm::json::Array{jocky::diagnostic_json(error.diagnostic, source)}}})
                << '\n';
    else
      std::cerr << jocky::render_diagnostic(error.diagnostic, source, filename);
    return 1;
  } catch (const std::exception &error) {
    std::cerr << "JOCKY E999: Internal frontend failure: " << error.what() << '\n';
    return 70;
  }
}
