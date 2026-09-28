// Standalone native-runtime acceptance; no LLVM, network or third-party package needed.
#include "jocky/runtime.h"
#include <cassert>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char **argv) {
  assert(argc == 2);
  std::filesystem::create_directories(argv[1]);
  std::ofstream fixture(std::filesystem::path(argv[1]) / "interop_fixture.py");
  fixture << "simulation = True\nsimulation_label = 'Python bridge test fixture'\n"
             "def format_value(value): return f'value={value}'\n"
             "def fail(): raise RuntimeError('fixture failure\\nsecond line')\n"
             "def unsupported(): return []\n"
             "def identity(value): return value\n"
             "def nothing(): return None\n";
  fixture.close();
  setenv("JOCKY_PYTHON_PACKAGES_DIR", argv[1], 1);
  jocky_context *context = nullptr;
  assert(jocky_rt_fixture_context_create(&context) == JOCKY_OK);
  auto call = [&](std::string module, std::string function, std::string arguments) {
    std::string config = "{\"module\":\"" + module + "\",\"function\":\"" + function +
                         "\",\"arguments\":" + arguments + ",\"result_name\":\"formatted\"}";
    jocky_dataset_handle handle = 99;
    auto status = jocky_rt_analysis(context, 0, "PYTHON_CALL", 11,
                                    reinterpret_cast<const uint8_t *>(config.data()), config.size(),
                                    nullptr, 0, &handle);
    if (status == JOCKY_OK) {
      assert(handle != 0);
      assert(jocky_rt_dataset_release(context, handle) == JOCKY_OK);
    } else
      assert(handle == 0);
    return status;
  };
  auto status = call("interop_fixture", "format_value", "[{\"type\":\"int\",\"value\":\"123\"}]");
  if (status == JOCKY_UNAVAILABLE) {
    auto error = jocky_rt_last_error(context);
    assert(std::string(error.code, error.code_size) == "PYTHON_UNAVAILABLE");
    std::cout << "PASS optional Python UNAVAILABLE\n";
    jocky_rt_context_destroy(context);
    return 0;
  }
  assert(status == JOCKY_OK);
  auto result = [&] {
    const char *name, *value;
    size_t name_size, value_size;
    assert(jocky_rt_fixture_python_result(context, 0, &name, &name_size, &value, &value_size));
    assert(std::string(name, name_size) == "formatted");
    return std::string(value, value_size);
  };
  assert(result() == "value=123");
  for (const auto &[type, value, expected] : {std::tuple{"string", "true", "true"},
                                              {"int", "-12", "-12"},
                                              {"float", "1.25", "1.25"},
                                              {"bool", "true", "true"},
                                              {"bool", "false", "false"}}) {
    assert(call("interop_fixture", "identity",
                "[{\"type\":\"" + std::string(type) + "\",\"value\":\"" + value + "\"}]") ==
           JOCKY_OK);
    assert(result() == expected);
  }
  assert(call("interop_fixture", "nothing", "[]") == JOCKY_OK);
  assert(result() == "null");
  for (const auto &[module, function, code] :
       {std::tuple{"jocky_missing_fixture_xyz", "f", "PYTHON_MODULE_UNAVAILABLE"},
        {"interop_fixture", "xyz", "PYTHON_FUNCTION_UNAVAILABLE"},
        {"interop_fixture", "fail", "PYTHON_CALL_FAILED"},
        {"interop_fixture", "unsupported", "PYTHON_CALL_FAILED"}}) {
    assert(call(module, function, "[]") != JOCKY_OK);
    auto error = jocky_rt_last_error(context);
    assert(std::string(error.code, error.code_size) == code);
    if (std::string(function) == "fail")
      assert(std::string(error.message, error.message_size) == "fixture failure?second line");
  }
  // Errors do not poison subsequent calls or release the retained display result.
  assert(call("interop_fixture", "nothing", "[]") == JOCKY_OK);
  jocky_rt_context_destroy(context);
  std::cout << "PASS Python bridge calls, scalar returns, result lifetime and clean failures\n";
}
