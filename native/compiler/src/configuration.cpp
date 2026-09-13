#include "jocky/semantic.h"
#include <algorithm>
#include <charconv>
#include <iomanip>
#include <sstream>

namespace jocky {
void SemanticAnalyzer::configuration() {
  module_.hunt_name = program_.hunt_name;
  module_.case_name = program_.case_name;
  if (program_.hunt_name.empty())
    fail("E230", "Hunt name must not be empty.", program_.span);
  std::set<std::string> seen;
  for (const auto &cap : program_.capabilities) {
    if (!capability_names().contains(cap))
      fail("E240", "Unknown capability `" + cap + "`.", program_.span);
    if (!seen.insert(cap).second)
      fail("E240", "Duplicate capability `" + cap + "`.", program_.span);
  }
  seen.clear();
  for (const auto &selector : program_.selectors) {
    if (selector.kind == "os") {
      if (selector.value != "windows" && selector.value != "linux")
        fail("E231", "Invalid target OS `" + selector.value + "`.", selector.span,
             "Endpoint targets are windows and linux; macOS is a development host.");
      if (seen.insert("os:" + selector.value).second)
        module_.target_os.push_back(selector.value);
    } else {
      if (selector.value.empty() || selector.value.find('\0') != std::string::npos)
        fail("E231", "Target selector cannot be empty or contain NUL.", selector.span);
      if (!seen.insert(selector.kind + ":" + selector.value).second)
        fail("E231", "Duplicate target selector.", selector.span);
      module_.targets.push_back(
          llvm::json::Object{{"kind", selector.kind}, {"value", selector.value}});
    }
  }
  if (module_.target_os.empty())
    module_.target_os = {"linux", "windows"};
  std::sort(module_.target_os.begin(), module_.target_os.end());
  module_.warnings.push_back(
      {"W250", "Selectors are unresolved; this plan is not authorized for dispatch.", program_.span,
       "Resolve enrolled endpoints and enforce local policy before execution.", "warning"});
  module_.warnings.push_back(
      {"W251", "LLVM source lowering, collectors and resource enforcement are not implemented.",
       program_.span, "This is a real static frontend plan, not an execution result.", "warning"});
  module_.budget = llvm::json::Object{{"schema_version", "1.0.0"},
                                      {"cpu_percent", 20},
                                      {"memory_bytes", 256000000},
                                      {"io_bytes", 150000000},
                                      {"duration_ms", 120000}};
  for (const auto &[key, option] : program_.budgets) {
    if (key != "cpu" && key != "memory" && key != "io" && key != "duration")
      fail("E232", "Unknown resource budget `" + key + "`.", option.span);
    if (option.value->literal_kind != "quantity")
      fail("E232", "Budget requires an integer and explicit unit.", option.span);
    auto v = quantity(option.value->value,
                      key == "cpu"        ? "cpu"
                      : key == "duration" ? "duration"
                                          : "bytes",
                      option.span);
    if ((key != "io" && v == 0) || (key == "cpu" && v > 100) || (key == "duration" && v > 86400000))
      fail("E232", "Budget is outside the allowed range.", option.span);
    module_.budget[key == "cpu"      ? "cpu_percent"
                   : key == "memory" ? "memory_bytes"
                   : key == "io"     ? "io_bytes"
                                     : "duration_ms"] = v;
  }
  if (program_.budgets.size() < 4)
    module_.warnings.push_back(
        {"W232", "Omitted budgets use explicit conservative defaults shown in the plan.",
         program_.span, "Declare all four budgets for operator review.", "warning"});
  module_.runtime = llvm::json::Object{{"backend", "llvm"}, {"execution", "memory"}};
  for (const auto &[key, option] : program_.runtime) {
    if (key == "variant")
      continue;
    if (key != "backend" && key != "execution")
      fail("E233", "Unknown runtime option `" + key + "`.", option.span);
    auto v = option.value->value;
    if (key == "backend" && v != "llvm")
      fail("E233", "LLVM is the mandatory backend.", option.span);
    if (key == "execution" && v != "memory" && v != "native")
      fail("E234", "Invalid or unavailable execution mode `" + v + "`.", option.span,
           "Use native or memory. Optional VM is not implemented.");
    module_.runtime[key] = v;
  }
  llvm::json::Object variant{{"enabled", false},
                             {"seed", "auto"},
                             {"profile", "balanced"},
                             {"seed_resolution", "DEFERRED_TO_BUILD_FORGE"}};
  for (const auto &[key, option] : program_.variant) {
    auto v = option.value->value;
    if (key == "enabled") {
      if (option.value->literal_kind != "bool")
        fail("E235", "variant.enabled requires a boolean.", option.span);
      variant[key] = v == "true";
    } else if (key == "profile") {
      if (v != "balanced" && v != "minimal")
        fail("E235", "Invalid variant profile `" + v + "`.", option.span);
      variant[key] = v;
    } else if (key == "seed") {
      if (v != "auto") {
        uint64_t seed = 0;
        std::string digits = v.starts_with("0x") ? v.substr(2) : v;
        int base = v.starts_with("0x") || option.value->literal_kind == "string" ? 16 : 10;
        auto result = std::from_chars(digits.data(), digits.data() + digits.size(), seed, base);
        if (digits.empty() || result.ec != std::errc() ||
            result.ptr != digits.data() + digits.size())
          fail("E235", "Variant seed must be auto or an unsigned 64-bit integer.", option.span);
        std::ostringstream out;
        out << std::hex << std::setw(16) << std::setfill('0') << seed;
        variant[key] = out.str();
        variant["seed_resolution"] = "EXPLICIT";
      }
    } else
      fail("E235", "Unknown variant option `" + key + "`.", option.span);
  }
  module_.runtime["variant"] = std::move(variant);
}
} // namespace jocky
