#include "jocky/backend.h"
#include "jocky/llvm_probe.h"
#include "jocky/parser.h"
#include "jocky/semantic.h"

#include <charconv>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <llvm/Config/llvm-config.h>
#include <llvm/Support/FormatVariadic.h>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;

double elapsed_ms(Clock::time_point start) {
  return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

struct CommandLine {
  std::string command;
  std::vector<std::string> positional;
  std::map<std::string, std::string> options;
  bool json = false;
};

struct FrontendResult {
  std::string source;
  jocky::Program program;
  jocky::FrontendModule module;
  jocky::StageProfile profile;
};

CommandLine command_line(int argc, char **argv) {
  CommandLine result;
  if (argc > 1)
    result.command = argv[1];
  const std::set<std::string> valued{"--target", "--execution", "--output", "--seed", "--count"};
  for (int index = 2; index < argc; ++index) {
    std::string argument = argv[index];
    if (argument == "--json") {
      result.json = true;
    } else if (argument.starts_with("--")) {
      if (!valued.contains(argument) || index + 1 >= argc)
        jocky::fail("E001", "Unknown option or missing option value `" + argument + "`.", {});
      if (!result.options.emplace(argument, argv[++index]).second)
        jocky::fail("E001", "Duplicate command option `" + argument + "`.", {});
    } else {
      result.positional.push_back(argument);
    }
  }
  return result;
}

std::string read_source(const std::string &filename) {
  std::ifstream input(filename, std::ios::binary);
  if (!input)
    jocky::fail("E003", "Cannot open source file.", {});
  std::string source(262145, '\0');
  input.read(source.data(), static_cast<std::streamsize>(source.size()));
  source.resize(static_cast<size_t>(input.gcount()));
  if (input.bad())
    jocky::fail("E003", "Failed to read source file.", {});
  return source;
}

std::string file_sha256(const std::filesystem::path &path) {
  std::ifstream input(path, std::ios::binary);
  if (!input)
    jocky::fail("E265", "Cannot read artifact for manifest verification.", {});
  std::ostringstream bytes;
  bytes << input.rdbuf();
  return jocky::sha256(bytes.str());
}

FrontendResult frontend(const std::string &filename) {
  FrontendResult result;
  result.source = read_source(filename);
  auto start = Clock::now();
  auto tokens = jocky::lex(result.source);
  result.profile.lex_ms = elapsed_ms(start);
  start = Clock::now();
  result.program = jocky::Parser(std::move(tokens)).parse();
  result.profile.parse_ms = elapsed_ms(start);
  start = Clock::now();
  result.module = jocky::SemanticAnalyzer(result.program, result.source).analyze();
  result.profile.semantic_ms = elapsed_ms(start);
  start = Clock::now();
  (void)jocky::canonical_json(jocky::jir_json(result.module));
  result.profile.jir_ms = elapsed_ms(start);
  return result;
}

uint64_t parse_seed(const std::string &text) {
  std::string digits = text;
  int base = 10;
  if (digits.starts_with("0x")) {
    digits = digits.substr(2);
    base = 16;
  } else if (digits.size() == 16) {
    base = 16;
  }
  uint64_t value = 0;
  auto converted = std::from_chars(digits.data(), digits.data() + digits.size(), value, base);
  if (digits.empty() || converted.ec != std::errc() ||
      converted.ptr != digits.data() + digits.size())
    jocky::fail("E261", "Seed must be an unsigned 64-bit decimal or hexadecimal value.", {});
  return value;
}

uint64_t selected_seed(const FrontendResult &compiled, const CommandLine &cli) {
  if (auto found = cli.options.find("--seed"); found != cli.options.end())
    return parse_seed(found->second);
  auto *variant = compiled.module.runtime.getObject("variant");
  auto configured =
      variant == nullptr ? std::optional<llvm::StringRef>{} : variant->getString("seed");
  if (configured && *configured != "auto")
    return parse_seed(configured->str());
  return parse_seed(compiled.module.source_hash.substr(0, 16));
}

bool protect_literals(const jocky::FrontendModule &module) {
  return module.runtime.getBoolean("protect_literals").value_or(false);
}

jocky::VariantOptions variant_options(const FrontendResult &compiled, const CommandLine &cli,
                                      uint64_t seed, const std::string &mode) {
  jocky::VariantOptions options;
  options.seed = seed;
  options.target_triple = cli.options.contains("--target") ? cli.options.at("--target") : "host";
  options.execution_mode = mode;
  if (auto *variant = compiled.module.runtime.getObject("variant"))
    options.profile = variant->getString("profile").value_or("balanced").str();
  options.protect_literals = protect_literals(compiled.module);
  if (options.protect_literals) {
    const char *key = std::getenv("JOCKY_LITERAL_KEY_HEX");
    const char *key_id = std::getenv("JOCKY_LITERAL_KEY_ID");
    if (key == nullptr || key_id == nullptr || std::string(key_id).empty())
      jocky::fail("E262",
                  "protect_literals requires JOCKY_LITERAL_KEY_HEX and JOCKY_LITERAL_KEY_ID.", {});
    options.literal_key = jocky::parse_aes256_key_hex(key);
    options.literal_key_id = key_id;
  }
  return options;
}

void merge_frontend_profile(jocky::StageProfile &target,
                            const jocky::StageProfile &frontend_profile) {
  target.lex_ms = frontend_profile.lex_ms;
  target.parse_ms = frontend_profile.parse_ms;
  target.semantic_ms = frontend_profile.semantic_ms;
  target.jir_ms = frontend_profile.jir_ms;
}

void configure_fixture_key(jocky_context *context, const jocky::VariantOptions &options) {
  if (!options.protect_literals)
    return;
  if (jocky_rt_set_literal_key(context, options.literal_key_id.data(),
                               options.literal_key_id.size(), options.literal_key.data(),
                               options.literal_key.size()) != JOCKY_OK)
    jocky::fail("E262", "Runtime rejected the protected-literal key.", {});
}

std::string fixture_hash(jocky_context *context) {
  char output[65]{};
  if (jocky_rt_fixture_semantic_hash(context, output, sizeof(output)) != JOCKY_OK)
    jocky::fail("E266", "Fixture runtime did not produce a semantic hash.", {});
  return output;
}

std::string required_option(const CommandLine &cli, const std::string &name) {
  auto found = cli.options.find(name);
  if (found == cli.options.end() || found->second.empty())
    jocky::fail("E001", "Command requires `" + name + " <value>`.", {});
  return found->second;
}

size_t count_option(const CommandLine &cli, size_t fallback) {
  auto found = cli.options.find("--count");
  if (found == cli.options.end())
    return fallback;
  uint64_t count = parse_seed(found->second);
  if (count == 0 || count > 64)
    jocky::fail("E261", "Variant count must be between 1 and 64.", {});
  return static_cast<size_t>(count);
}

std::string object_suffix() {
#ifdef _WIN32
  return ".obj";
#else
  return ".o";
#endif
}

void validate_target_mode(const CommandLine &cli, const std::string &required_mode) {
  auto target = cli.options.contains("--target") ? cli.options.at("--target") : "host";
  if (target != "host" && target != "linux-x86_64" && target != "linux-aarch64" &&
      target != "windows-x86_64")
    jocky::fail("E263",
                "Unsupported target. Use host, linux-x86_64, linux-aarch64 or windows-x86_64.", {});
  if (target != "host" && cli.command != "compile" && cli.command != "llvm")
    jocky::fail("E263", "Cross-target fixture/JIT execution requires that target host.", {});
  auto mode = cli.options.contains("--execution") ? cli.options.at("--execution") : required_mode;
  if (mode != required_mode)
    jocky::fail("E263", "This command requires --execution " + required_mode + ".", {});
}

llvm::json::Object execution_json(const jocky::LoweredVariant &variant,
                                  const jocky::StageProfile &profile) {
  return llvm::json::Object{{"schema_version", "1.0.0"},
                            {"kind", "JockyExecution"},
                            {"status", "OK"},
                            {"simulation", true},
                            {"simulation_label", "DETERMINISTIC_COMPILER_FIXTURE"},
                            {"manifest", jocky::manifest_json(variant.manifest)},
                            {"profile", jocky::profile_json(profile)}};
}
} // namespace

int main(int argc, char **argv) {
  std::string source;
  std::string filename = "<command>";
  bool json = false;
  try {
    auto cli = command_line(argc, argv);
    json = cli.json;
    if (cli.command == "--version" && cli.positional.empty()) {
      std::cout << "jockyc " << jocky::compiler_version << " (LLVM " << LLVM_VERSION_STRING
                << "; runtime ABI " << JOCKY_RUNTIME_ABI_VERSION << ")\n";
      return 0;
    }
    if (cli.command == "--self-test" && cli.positional.empty()) {
      std::string error;
      if (!jocky::verify_orc_toolchain(error)) {
        std::cerr << "JOCKY E002: " << error << '\n';
        return 70;
      }
      std::cout << "PASS: LLVM ORC toolchain and runtime ABI probe\n";
      return 0;
    }
    if (cli.command == "--help" && cli.positional.empty()) {
      std::cout
          << "jockyc check|tokens|ast|jir|llvm|plan <file.jky> [--json] [--seed N]\n"
             "jockyc compile <file.jky> --target host --execution native --output <object>\n"
             "jockyc run <file.jky> --execution memory [--json] [--seed N]\n"
             "jockyc variants <file.jky> --count N [--output <directory>] [--json]\n"
             "jockyc variant-info <manifest-or-artifact> [--json]\n"
             "jockyc benchmark <file.jky> [--count N] [--json]\n"
             "JIT/variant verification uses a clearly labeled deterministic fixture runtime.\n";
      return 0;
    }
    if (cli.positional.size() != 1)
      jocky::fail("E001", "Expected exactly one source, manifest, or artifact path.", {});
    filename = cli.positional.front();

    if (cli.command == "variant-info") {
      std::filesystem::path path(filename);
      const bool artifact = path.extension() != ".json";
      auto manifest_path =
          artifact ? std::filesystem::path(path.string() + ".manifest.json") : path;
      auto manifest = jocky::read_manifest(manifest_path.string());
      if (artifact) {
        auto actual = file_sha256(path);
        if (!manifest.artifact_hash || *manifest.artifact_hash != actual)
          jocky::fail("E265", "Artifact bytes do not match the manifest SHA-256.", {});
      }
      if (json)
        std::cout << jocky::canonical_json(jocky::manifest_json(manifest)) << '\n';
      else
        std::cout << jocky::manifest_summary(manifest);
      return 0;
    }

    source = read_source(filename);
    if (cli.command == "tokens") {
      auto tokens = jocky::lex(source);
      llvm::json::Value output = llvm::json::Object{{"schema_version", "1.0.0"},
                                                    {"kind", "TokenStream"},
                                                    {"tokens", jocky::tokens_json(tokens)}};
      std::cout << (json ? jocky::canonical_json(output) : llvm::formatv("{0:2}", output).str())
                << '\n';
      return 0;
    }
    auto compiled = frontend(filename);
    llvm::json::Value output = nullptr;
    if (cli.command == "ast") {
      output = jocky::ast_json(compiled.program);
    } else if (cli.command == "jir") {
      output = jocky::jir_json(compiled.module);
    } else if (cli.command == "plan") {
      output = jocky::plan_json(compiled.module);
    } else if (cli.command == "check") {
      llvm::json::Array warnings;
      for (const auto &warning : compiled.module.warnings)
        warnings.push_back(jocky::diagnostic_json(warning, compiled.source));
      output = llvm::json::Object{
          {"schema_version", "1.0.0"},
          {"kind", "FrontendCheck"},
          {"valid", true},
          {"hunt", compiled.program.hunt_name},
          {"source_hash", compiled.module.source_hash},
          {"jir_hash", jocky::sha256(jocky::canonical_json(jocky::jir_json(compiled.module)))},
          {"instruction_count", static_cast<int64_t>(compiled.module.instructions.size())},
          {"warnings", std::move(warnings)},
          {"executable", false}};
      if (!json) {
        std::cout << "PASS: " << compiled.program.hunt_name << " â€” "
                  << compiled.module.instructions.size() << " typed JIR instructions\n";
        std::cout << "LLVM lowering is available; endpoint execution still requires an "
                     "authorized runtime host.\n";
        for (const auto &warning : compiled.module.warnings)
          std::cerr << jocky::render_diagnostic(warning, compiled.source, filename);
        return 0;
      }
    } else if (cli.command == "llvm") {
      validate_target_mode(cli, "memory");
      auto options = variant_options(compiled, cli, selected_seed(compiled, cli), "memory");
      auto variant = jocky::lower_to_llvm(compiled.module, options);
      merge_frontend_profile(variant.profile, compiled.profile);
      auto ir = jocky::render_llvm_ir(variant);
      if (auto found = cli.options.find("--output"); found != cli.options.end()) {
        std::ofstream file(found->second, std::ios::binary);
        if (!file)
          jocky::fail("E264", "Cannot create LLVM IR output.", {});
        file << ir;
      }
      if (json)
        std::cout << jocky::canonical_json(
                         llvm::json::Object{{"schema_version", "1.0.0"},
                                            {"kind", "LLVMModule"},
                                            {"ir", ir},
                                            {"manifest", jocky::manifest_json(variant.manifest)},
                                            {"profile", jocky::profile_json(variant.profile)}})
                  << '\n';
      else
        std::cout << ir;
      return 0;
    } else if (cli.command == "compile") {
      validate_target_mode(cli, "native");
      auto path = required_option(cli, "--output");
      auto options = variant_options(compiled, cli, selected_seed(compiled, cli), "native");
      auto variant = jocky::lower_to_llvm(compiled.module, options);
      merge_frontend_profile(variant.profile, compiled.profile);
      jocky::emit_aot_object(variant, path);
      jocky::write_manifest(variant.manifest, path + ".manifest.json");
      if (json)
        std::cout << jocky::canonical_json(
                         llvm::json::Object{{"manifest", jocky::manifest_json(variant.manifest)},
                                            {"profile", jocky::profile_json(variant.profile)}})
                  << '\n';
      else
        std::cout << "AOT object: " << path << '\n'
                  << "Manifest: " << path << ".manifest.json\n"
                  << "Artifact SHA-256: " << *variant.manifest.artifact_hash << '\n';
      return 0;
    } else if (cli.command == "run") {
      validate_target_mode(cli, "memory");
      auto options = variant_options(compiled, cli, selected_seed(compiled, cli), "memory");
      auto variant = jocky::lower_to_llvm(compiled.module, options);
      merge_frontend_profile(variant.profile, compiled.profile);
      jocky_context *context = nullptr;
      if (jocky_rt_fixture_context_create(&context) != JOCKY_OK)
        jocky::fail("E266", "Cannot create deterministic fixture runtime.", {});
      configure_fixture_key(context, options);
      std::string error;
      auto status = jocky::execute_orc(std::move(variant), context, variant.profile, error);
      if (status != JOCKY_OK) {
        auto detail = jocky_rt_last_error(context);
        std::string message(detail.message, detail.message_size);
        jocky_rt_context_destroy(context);
        jocky::fail("E266", "ORC execution failed: " + (error.empty() ? message : error), {});
      }
      auto semantic_hash = fixture_hash(context);
      jocky_rt_context_destroy(context);
      variant.manifest.semantic_result_hash = semantic_hash;
      if (json)
        std::cout << jocky::canonical_json(execution_json(variant, variant.profile)) << '\n';
      else
        std::cout << "PASS: ORC executed compiler-generated code in this JOCKY process\n"
                  << "Fixture: SIMULATED deterministic collector\n"
                  << "Semantic result SHA-256: " << semantic_hash << '\n'
                  << jocky::canonical_json(jocky::profile_json(variant.profile)) << '\n';
      return 0;
    } else if (cli.command == "variants" || cli.command == "benchmark") {
      validate_target_mode(cli, "native");
      auto count = count_option(cli, 3);
      auto base_seed = selected_seed(compiled, cli);
      std::filesystem::path directory;
      const bool persist = cli.command == "variants";
      if (persist) {
        directory = cli.options.contains("--output")
                        ? std::filesystem::path(cli.options.at("--output"))
                        : std::filesystem::path(std::filesystem::path(filename).stem().string() +
                                                ".variants");
        std::filesystem::create_directories(directory);
      } else {
        directory = std::filesystem::temp_directory_path() /
                    ("jocky-benchmark-" + compiled.module.source_hash.substr(0, 12));
        std::filesystem::create_directories(directory);
      }
      llvm::json::Array records;
      std::optional<std::string> expected_semantics;
      std::vector<jocky::VariantManifest> manifests;
      for (size_t index = 0; index < count; ++index) {
        auto options = variant_options(compiled, cli, base_seed + index, "native");
        auto variant = jocky::lower_to_llvm(compiled.module, options);
        merge_frontend_profile(variant.profile, compiled.profile);
        auto object = directory / (variant.manifest.variant_id + object_suffix());
        jocky::emit_aot_object(variant, object.string());
        jocky_context *context = nullptr;
        if (jocky_rt_fixture_context_create(&context) != JOCKY_OK)
          jocky::fail("E266", "Cannot create deterministic fixture runtime.", {});
        configure_fixture_key(context, options);
        std::string error;
        auto status = jocky::execute_orc(std::move(variant), context, variant.profile, error);
        if (status != JOCKY_OK) {
          jocky_rt_context_destroy(context);
          jocky::fail("E266", "Variant ORC execution failed: " + error, {});
        }
        auto semantic_hash = fixture_hash(context);
        jocky_rt_context_destroy(context);
        variant.manifest.semantic_result_hash = semantic_hash;
        if (expected_semantics && *expected_semantics != semantic_hash)
          jocky::fail("E266", "Variant semantic-equivalence verification failed.", {});
        expected_semantics = semantic_hash;
        if (persist)
          jocky::write_manifest(variant.manifest, object.string() + ".manifest.json");
        records.push_back(
            llvm::json::Object{{"manifest", jocky::manifest_json(variant.manifest)},
                               {"profile", jocky::profile_json(variant.profile)},
                               {"artifact_path", persist ? llvm::json::Value(object.string())
                                                         : llvm::json::Value(nullptr)}});
        manifests.push_back(variant.manifest);
        if (!persist)
          std::filesystem::remove(object);
      }
      if (!persist)
        std::filesystem::remove(directory);
      if (json || cli.command == "benchmark") {
        std::cout << jocky::canonical_json(
                         llvm::json::Object{{"schema_version", "1.0.0"},
                                            {"kind", persist ? "VariantSet" : "CompilerBenchmark"},
                                            {"simulation", true},
                                            {"simulation_label", "DETERMINISTIC_COMPILER_FIXTURE"},
                                            {"semantic_equivalence", true},
                                            {"samples", std::move(records)}})
                  << '\n';
      } else {
        std::cout << "SEED              VARIANT          BLOCKS FUNCTIONS HELPERS ARTIFACT\n";
        for (const auto &manifest : manifests)
          std::cout << manifest.variant_seed << ' ' << manifest.variant_id.substr(0, 16) << ' '
                    << std::setw(6) << manifest.structural.basic_block_count << ' ' << std::setw(9)
                    << manifest.structural.function_count << ' ' << std::setw(7)
                    << manifest.structural.generated_helper_count << ' '
                    << manifest.artifact_hash->substr(0, 16) << '\n';
        std::cout << "Semantic equivalence: PASS (fixture SHA-256 " << *expected_semantics
                  << ")\nOutput: " << directory.string() << '\n';
      }
      return 0;
    } else {
      jocky::fail("E001", "Unknown command `" + cli.command + "`; see --help.", {});
    }

    std::cout << (json ? jocky::canonical_json(output) : llvm::formatv("{0:2}", output).str())
              << '\n';
    return 0;
  } catch (const jocky::FrontendError &error) {
    if (json)
      std::cout << jocky::canonical_json(llvm::json::Object{
                       {"schema_version", "1.0.0"},
                       {"kind", "CompilerFailure"},
                       {"valid", false},
                       {"diagnostics",
                        llvm::json::Array{jocky::diagnostic_json(error.diagnostic, source)}}})
                << '\n';
    else
      std::cerr << jocky::render_diagnostic(error.diagnostic, source, filename);
    return 1;
  } catch (const std::exception &error) {
    std::cerr << "JOCKY E999: Internal compiler failure: " << error.what() << '\n';
    return 70;
  }
}
