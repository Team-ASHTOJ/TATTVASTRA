#include "jocky/python_bridge.h"
#ifdef JOCKY_WITH_PYTHON
#include <Python.h>
#include <cstdlib>
#include <mutex>
#include <stdexcept>

namespace {
struct Object {
  PyObject *p;
  explicit Object(PyObject *value) : p(value) {}
  ~Object() { Py_XDECREF(p); }
  Object(const Object &) = delete;
};
struct Gil {
  PyGILState_STATE state = PyGILState_Ensure();
  ~Gil() {
    PyErr_Clear();
    PyGILState_Release(state);
  }
};
std::string text(PyObject *value) {
  Py_ssize_t size = 0;
  const char *bytes = value ? PyUnicode_AsUTF8AndSize(value, &size) : nullptr;
  if (!bytes)
    throw std::runtime_error("Expected UTF-8 text");
  return std::string(bytes, static_cast<size_t>(size));
}
PyObject *field(PyObject *dict, const char *key) {
  if (!dict || !PyDict_Check(dict))
    throw std::runtime_error("Invalid Python call configuration");
  auto *value = PyDict_GetItemString(dict, key);
  if (!value)
    throw std::runtime_error("Incomplete Python call configuration");
  return value;
}
std::string exception_text() {
  PyObject *type = nullptr, *value = nullptr, *trace = nullptr;
  PyErr_Fetch(&type, &value, &trace);
  PyErr_NormalizeException(&type, &value, &trace);
  Object t(type), v(value), tb(trace);
  Object message(value ? PyObject_Str(value) : nullptr);
  std::string result = "Python operation failed";
  if (message.p) {
    try {
      result = text(message.p);
    } catch (...) {
    }
  }
  // One bounded printable line, without traceback or terminal control sequences.
  if (result.size() > 240)
    result.resize(240);
  for (char &c : result)
    if (static_cast<unsigned char>(c) < 32 || static_cast<unsigned char>(c) >= 127)
      c = '?';
  PyErr_Clear();
  return result;
}
} // namespace
#endif

namespace jocky {
jocky_status python_call(std::string_view config, PythonResult &result) noexcept {
  result = {};
#ifndef JOCKY_WITH_PYTHON
  (void)config;
  result.code = "PYTHON_UNAVAILABLE";
  result.message = "Python development support was unavailable when this runtime was built.";
  return JOCKY_UNAVAILABLE;
#else
  try {
    static std::once_flag initialized;
    std::call_once(initialized, [] {
      if (!Py_IsInitialized()) {
        PyConfig configuration;
        PyConfig_InitPythonConfig(&configuration);
        configuration.install_signal_handlers = 0;
        auto status = Py_InitializeFromConfig(&configuration);
        PyConfig_Clear(&configuration);
        if (PyStatus_Exception(status))
          throw std::runtime_error("Cannot initialize Python");
        PyEval_SaveThread();
      }
    });
    Gil gil;
    try {
      Object json(PyImport_ImportModule("json"));
      Object config_text(PyUnicode_DecodeUTF8(config.data(), config.size(), "strict"));
      Object parsed(json.p && config_text.p
                        ? PyObject_CallMethod(json.p, "loads", "O", config_text.p)
                        : nullptr);
      if (!parsed.p)
        throw std::runtime_error("Invalid Python call configuration");
      auto module_name = text(field(parsed.p, "module"));
      auto function_name = text(field(parsed.p, "function"));
      result.name = text(field(parsed.p, "result_name"));
      auto *args = field(parsed.p, "arguments");
      if (!PyList_Check(args))
        throw std::runtime_error("Invalid Python arguments");
      const char *override_path = std::getenv("JOCKY_PYTHON_PACKAGES_DIR");
      const char *home = std::getenv("HOME");
      if (!override_path && !home)
        throw std::runtime_error("HOME is unavailable");
      std::string path =
          override_path ? override_path : std::string(home) + "/.jocky/python/site-packages";
      if (path.starts_with("~/") && home)
        path = std::string(home) + path.substr(1);
      Object package_path(PyUnicode_DecodeFSDefault(path.c_str()));
      auto *sys_path = PySys_GetObject("path");
      if (!package_path.p || !sys_path || PyList_Insert(sys_path, 0, package_path.p) < 0)
        throw std::runtime_error("Cannot add JOCKY package directory");
      Object module(PyImport_ImportModule(module_name.c_str()));
      if (!module.p) {
        if (PyErr_ExceptionMatches(PyExc_ModuleNotFoundError)) {
          PyErr_Clear();
          result.code = "PYTHON_MODULE_UNAVAILABLE";
          result.message = "Python module `" + module_name +
                           "` is not installed.\nRun: jocky install " + module_name;
          return JOCKY_UNAVAILABLE;
        }
        throw std::runtime_error("Python module import failed");
      }
      Object callable(PyObject_GetAttrString(module.p, function_name.c_str()));
      if (!callable.p || !PyCallable_Check(callable.p) || PyType_Check(callable.p)) {
        PyErr_Clear();
        result.code = "PYTHON_FUNCTION_UNAVAILABLE";
        result.message = "Module `" + module_name + "` has no callable `" + function_name + "`.";
        return JOCKY_UNAVAILABLE;
      }
      Object tuple(PyTuple_New(PyList_Size(args)));
      if (!tuple.p)
        throw std::runtime_error("Cannot allocate Python arguments");
      for (Py_ssize_t i = 0; i < PyList_Size(args); ++i) {
        auto *arg = PyList_GetItem(args, i);
        auto type = text(field(arg, "type"));
        auto *value = field(arg, "value");
        auto bytes = text(value);
        PyObject *converted = nullptr;
        if (type == "string") {
          converted = value;
          Py_INCREF(converted);
        } else if (type == "int")
          converted = PyLong_FromUnicodeObject(value, 10);
        else if (type == "float")
          converted = PyFloat_FromString(value);
        else if (type == "bool" && (bytes == "true" || bytes == "false"))
          converted = PyBool_FromLong(bytes == "true");
        if (!converted)
          throw std::runtime_error("Unsupported Python argument");
        PyTuple_SET_ITEM(tuple.p, i, converted);
      }
      Object output(PyObject_CallObject(callable.p, tuple.p));
      if (!output.p)
        throw std::runtime_error("Python call failed");
      if (output.p == Py_None)
        result.value = "null";
      else if (PyBool_Check(output.p))
        result.value = output.p == Py_True ? "true" : "false";
      else if (PyUnicode_CheckExact(output.p))
        result.value = text(output.p);
      else if (PyLong_CheckExact(output.p) || PyFloat_CheckExact(output.p)) {
        Object rendered(PyObject_Str(output.p));
        result.value = text(rendered.p);
      } else
        throw std::runtime_error("Unsupported Python return type");
      return JOCKY_OK;
    } catch (const std::exception &error) {
      result.code = "PYTHON_CALL_FAILED";
      result.message = PyErr_Occurred() ? exception_text() : error.what();
      return JOCKY_INTERNAL_ERROR;
    }
  } catch (...) {
    result.code = "PYTHON_CALL_FAILED";
    result.message = "Python runtime initialization failed";
    return JOCKY_INTERNAL_ERROR;
  }
#endif
}
} // namespace jocky
