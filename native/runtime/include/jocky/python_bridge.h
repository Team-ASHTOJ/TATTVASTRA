#pragma once
#include "jocky/runtime.h"
#include <string>
#include <string_view>

namespace jocky {
struct PythonResult {
  std::string name;
  std::string value;
  std::string code;
  std::string message;
};
// Runtime-only: never called by frontend, lowering or AOT emission.
jocky_status python_call(std::string_view config, PythonResult &result) noexcept;
} // namespace jocky
