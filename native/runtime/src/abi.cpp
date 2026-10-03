#include "jocky/python_bridge.h"
#include "jocky/runtime.h"

#include <array>
#include <cstring>
#include <map>
#include <new>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <set>
#include <string>
#include <string_view>
#include <vector>

namespace {
struct LiteralPool {
  std::string key_id;
  std::vector<uint8_t> nonce;
  std::vector<uint8_t> tag;
  std::vector<uint8_t> ciphertext;
  std::vector<uint8_t> associated_data;
};

struct FixtureHost {
  std::string trace;
  std::map<jocky_dataset_handle, jocky::PythonResult> python_datasets;
  std::map<std::string, std::string> python_results;
  std::map<jocky_dataset_handle, size_t> references;
};

std::array<uint8_t, 32> digest(std::string_view bytes) {
  std::array<uint8_t, 32> output{};
  unsigned int size = 0;
  EVP_Digest(bytes.data(), bytes.size(), output.data(), &size, EVP_sha256(), nullptr);
  return output;
}

uint32_t read_u32(const uint8_t *data) {
  return static_cast<uint32_t>(data[0]) | (static_cast<uint32_t>(data[1]) << 8U) |
         (static_cast<uint32_t>(data[2]) << 16U) | (static_cast<uint32_t>(data[3]) << 24U);
}

std::string hex_digest(std::string_view bytes) {
  static constexpr char hex[] = "0123456789abcdef";
  auto value = digest(bytes);
  std::string result(64, '0');
  for (size_t i = 0; i < value.size(); ++i) {
    result[i * 2] = hex[value[i] >> 4U];
    result[i * 2 + 1] = hex[value[i] & 15U];
  }
  return result;
}
} // namespace

struct jocky_context {
  jocky_runtime_host_v1 host{};
  jocky_status last_status = JOCKY_OK;
  std::string last_code = "OK";
  std::string last_message;
  std::string literal_key_id;
  std::vector<uint8_t> literal_key;
  LiteralPool pool;
  bool fixture = false;
};

namespace {
void set_error(jocky_context *context, jocky_status status, std::string code, std::string message) {
  if (context == nullptr)
    return;
  context->last_status = status;
  context->last_code = std::move(code);
  context->last_message = std::move(message);
}

bool allowed_analysis(std::string_view opcode) {
  static const std::set<std::string_view> allowed{
      "PYTHON_CALL",     "EVENT_FILTER",   "EVENT_NORMALIZE", "DRIVER_RISK_LOOKUP",
      "FILTER",          "LIMIT",          "PROJECT",         "SORT",
      "GROUP",           "JOIN",           "CORRELATE",       "TIMELINE",
      "FINDING_CREATE",  "BIND",           "ARTIFACT_STORE",  "ARTIFACT_HASH",
      "MANIFEST_CREATE", "REPORT_GENERATE"};
  return allowed.contains(opcode);
}

jocky_status decrypt_pool_item(jocky_context *context, uint32_t instruction_id,
                               std::vector<uint8_t> &item) {
  if (context->pool.ciphertext.empty() || context->literal_key.size() != 32 ||
      context->pool.nonce.size() != 12 || context->pool.tag.size() != 16 ||
      context->literal_key_id != context->pool.key_id) {
    set_error(context, JOCKY_DENIED, "LITERAL_KEY_UNAVAILABLE",
              "Protected literal key or pool is unavailable.");
    return JOCKY_DENIED;
  }
  std::vector<uint8_t> plaintext(context->pool.ciphertext.size());
  auto *cipher = EVP_CIPHER_CTX_new();
  int written = 0, total = 0;
  bool ok = cipher != nullptr &&
            EVP_DecryptInit_ex(cipher, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) == 1 &&
            EVP_CIPHER_CTX_ctrl(cipher, EVP_CTRL_GCM_SET_IVLEN,
                                static_cast<int>(context->pool.nonce.size()), nullptr) == 1 &&
            EVP_DecryptInit_ex(cipher, nullptr, nullptr, context->literal_key.data(),
                               context->pool.nonce.data()) == 1;
  if (ok && !context->pool.associated_data.empty())
    ok = EVP_DecryptUpdate(cipher, nullptr, &written, context->pool.associated_data.data(),
                           static_cast<int>(context->pool.associated_data.size())) == 1;
  if (ok)
    ok = EVP_DecryptUpdate(cipher, plaintext.data(), &written, context->pool.ciphertext.data(),
                           static_cast<int>(context->pool.ciphertext.size())) == 1;
  total = written;
  if (ok)
    ok = EVP_CIPHER_CTX_ctrl(cipher, EVP_CTRL_GCM_SET_TAG,
                             static_cast<int>(context->pool.tag.size()),
                             context->pool.tag.data()) == 1 &&
         EVP_DecryptFinal_ex(cipher, plaintext.data() + total, &written) == 1;
  total += written;
  EVP_CIPHER_CTX_free(cipher);
  if (!ok) {
    OPENSSL_cleanse(plaintext.data(), plaintext.size());
    set_error(context, JOCKY_DENIED, "LITERAL_AUTHENTICATION_FAILED",
              "Protected literal authentication failed.");
    return JOCKY_DENIED;
  }
  plaintext.resize(static_cast<size_t>(total));
  bool found = false;
  if (plaintext.size() >= 4) {
    size_t cursor = 4;
    const uint32_t count = read_u32(plaintext.data());
    for (uint32_t index = 0; index < count && cursor + 8 <= plaintext.size(); ++index) {
      const uint32_t id = read_u32(plaintext.data() + cursor);
      const uint32_t size = read_u32(plaintext.data() + cursor + 4);
      cursor += 8;
      if (size > plaintext.size() - cursor)
        break;
      if (id == instruction_id) {
        item.assign(plaintext.begin() + static_cast<std::ptrdiff_t>(cursor),
                    plaintext.begin() + static_cast<std::ptrdiff_t>(cursor + size));
        found = true;
        break;
      }
      cursor += size;
    }
  }
  OPENSSL_cleanse(plaintext.data(), plaintext.size());
  if (!found) {
    set_error(context, JOCKY_INVALID_ARGUMENT, "LITERAL_ITEM_MISSING",
              "Protected literal pool has no item for the instruction.");
    return JOCKY_INVALID_ARGUMENT;
  }
  return JOCKY_OK;
}

jocky_status dispatch(jocky_context *context, jocky_operation operation, uint32_t instruction_id,
                      std::string_view opcode, const uint8_t *config, size_t config_size,
                      const jocky_dataset_handle *inputs, size_t input_count,
                      jocky_dataset_handle *out) {
  if (out != nullptr)
    *out = JOCKY_DATASET_INVALID;
  if (context == nullptr || out == nullptr || context->host.invoke == nullptr ||
      (config == nullptr && config_size != 0) || (inputs == nullptr && input_count != 0))
    return JOCKY_INVALID_ARGUMENT;
  set_error(context, JOCKY_OK, "OK", "");
  std::vector<uint8_t> decrypted;
  if (config == nullptr && !context->pool.ciphertext.empty()) {
    auto status = decrypt_pool_item(context, instruction_id, decrypted);
    if (status != JOCKY_OK)
      return status;
    config = decrypted.data();
    config_size = decrypted.size();
  }
  if (operation == JOCKY_OP_ANALYSIS && opcode == "PYTHON_CALL") {
    if (!context->fixture) {
      set_error(context, JOCKY_UNAVAILABLE, "PYTHON_UNAVAILABLE",
                "Python interop requires the local runtime.");
      return JOCKY_UNAVAILABLE;
    }
    try {
      jocky::PythonResult result;
      auto status = jocky::python_call(
          std::string_view(reinterpret_cast<const char *>(config), config_size), result);
      if (!decrypted.empty())
        OPENSSL_cleanse(decrypted.data(), decrypted.size());
      if (status != JOCKY_OK) {
        set_error(context, status, result.code, result.message);
        return status;
      }
      auto *fixture = static_cast<FixtureHost *>(context->host.user_data);
      // A real one-row PythonResult dataset, owned by the existing handle lifecycle.
      uint64_t handle = 1;
      while (fixture->references.contains(handle))
        ++handle;
      fixture->python_datasets.emplace(handle, result);
      fixture->references[handle] = 1;
      fixture->python_results[result.name] = result.value;
      fixture->trace +=
          "PYTHON_CALL:" + hex_digest(result.name) + ":" + hex_digest(result.value) + "\n";
      *out = handle;
      return JOCKY_OK;
    } catch (...) {
      set_error(context, JOCKY_INTERNAL_ERROR, "PYTHON_CALL_FAILED", "Cannot store Python result.");
      return JOCKY_INTERNAL_ERROR;
    }
  }
  auto status =
      context->host.invoke(context->host.user_data, operation, instruction_id, opcode.data(),
                           opcode.size(), config, config_size, inputs, input_count, out);
  if (!decrypted.empty())
    OPENSSL_cleanse(decrypted.data(), decrypted.size());
  if (status != JOCKY_OK || *out == JOCKY_DATASET_INVALID) {
    if (status == JOCKY_OK)
      status = JOCKY_INTERNAL_ERROR;
    *out = JOCKY_DATASET_INVALID;
    set_error(context, status, "HOST_OPERATION_FAILED",
              "Runtime host operation did not produce an owned dataset.");
  }
  return status;
}

jocky_status fixture_invoke(void *user_data, jocky_operation operation, uint32_t instruction_id,
                            const char *opcode, size_t opcode_size, const uint8_t *config,
                            size_t config_size, const jocky_dataset_handle *inputs,
                            size_t input_count, jocky_dataset_handle *out) {
  auto *fixture = static_cast<FixtureHost *>(user_data);
  if (fixture == nullptr || out == nullptr)
    return JOCKY_INVALID_ARGUMENT;
  std::string record = std::to_string(static_cast<unsigned>(operation)) + ":" +
                       std::to_string(instruction_id) + ":" + std::string(opcode, opcode_size) +
                       ":";
  if (config != nullptr)
    record.append(reinterpret_cast<const char *>(config), config_size);
  for (size_t index = 0; index < input_count; ++index)
    record += ":" + std::to_string(inputs[index]);
  auto bytes = digest(record);
  uint64_t handle = 0;
  std::memcpy(&handle, bytes.data(), sizeof(handle));
  if (handle == 0)
    handle = 1;
  fixture->references[handle] += 1;
  fixture->trace += hex_digest(record) + "=" + std::to_string(handle) + "\n";
  OPENSSL_cleanse(record.data(), record.size());
  *out = handle;
  return JOCKY_OK;
}

jocky_status fixture_retain(void *user_data, jocky_dataset_handle handle) {
  auto *fixture = static_cast<FixtureHost *>(user_data);
  if (fixture == nullptr)
    return JOCKY_INVALID_ARGUMENT;
  auto found = fixture->references.find(handle);
  if (found == fixture->references.end())
    return JOCKY_INVALID_ARGUMENT;
  ++found->second;
  return JOCKY_OK;
}

jocky_status fixture_release(void *user_data, jocky_dataset_handle handle) {
  if (handle == JOCKY_DATASET_INVALID)
    return JOCKY_OK;
  auto *fixture = static_cast<FixtureHost *>(user_data);
  if (fixture == nullptr)
    return JOCKY_INVALID_ARGUMENT;
  auto found = fixture->references.find(handle);
  if (found == fixture->references.end())
    return JOCKY_INVALID_ARGUMENT;
  if (--found->second == 0) {
    fixture->python_datasets.erase(handle);
    fixture->references.erase(found);
  }
  return JOCKY_OK;
}

void fixture_destroy(void *user_data) { delete static_cast<FixtureHost *>(user_data); }

#define JOCKY_COLLECTOR(name, operation, opcode)                                                   \
  jocky_status name(jocky_context *context, uint32_t instruction_id, const uint8_t *config,        \
                    size_t config_size, jocky_dataset_handle *out) {                               \
    return dispatch(context, operation, instruction_id, opcode, config, config_size, nullptr, 0,   \
                    out);                                                                          \
  }
} // namespace

uint32_t jocky_rt_abi_version(void) { return JOCKY_RUNTIME_ABI_VERSION; }

jocky_status jocky_rt_context_create(const jocky_runtime_host_v1 *host, jocky_context **out) {
  if (out != nullptr)
    *out = nullptr;
  if (host == nullptr || out == nullptr || host->host_abi_version != JOCKY_RUNTIME_HOST_V1 ||
      host->struct_size < sizeof(jocky_runtime_host_v1) || host->invoke == nullptr ||
      host->retain == nullptr || host->release == nullptr)
    return JOCKY_INVALID_ARGUMENT;
  auto *context = new (std::nothrow) jocky_context;
  if (context == nullptr)
    return JOCKY_INTERNAL_ERROR;
  context->host = *host;
  *out = context;
  return JOCKY_OK;
}

void jocky_rt_context_destroy(jocky_context *context) {
  if (context == nullptr)
    return;
  if (!context->literal_key.empty())
    OPENSSL_cleanse(context->literal_key.data(), context->literal_key.size());
  if (context->host.destroy != nullptr)
    context->host.destroy(context->host.user_data);
  delete context;
}

jocky_error_view jocky_rt_last_error(const jocky_context *context) {
  if (context == nullptr)
    return {JOCKY_INVALID_ARGUMENT, "INVALID_CONTEXT", 15, "Context is null.", 16};
  return {context->last_status, context->last_code.data(), context->last_code.size(),
          context->last_message.data(), context->last_message.size()};
}

jocky_status jocky_rt_dataset_retain(jocky_context *context, jocky_dataset_handle handle) {
  if (context == nullptr || handle == JOCKY_DATASET_INVALID)
    return JOCKY_INVALID_ARGUMENT;
  return context->host.retain(context->host.user_data, handle);
}

jocky_status jocky_rt_dataset_release(jocky_context *context, jocky_dataset_handle handle) {
  if (context == nullptr)
    return JOCKY_INVALID_ARGUMENT;
  if (handle == JOCKY_DATASET_INVALID)
    return JOCKY_OK;
  return context->host.release(context->host.user_data, handle);
}

jocky_status jocky_rt_set_literal_key(jocky_context *context, const char *key_id,
                                      size_t key_id_size, const uint8_t *key, size_t key_size) {
  if (context == nullptr || key_id == nullptr || key_id_size == 0 || key == nullptr ||
      key_size != 32)
    return JOCKY_INVALID_ARGUMENT;
  if (!context->literal_key.empty())
    OPENSSL_cleanse(context->literal_key.data(), context->literal_key.size());
  context->literal_key_id.assign(key_id, key_id_size);
  context->literal_key.assign(key, key + key_size);
  return JOCKY_OK;
}

jocky_status jocky_rt_register_literal_pool(jocky_context *context, const char *key_id,
                                            size_t key_id_size, const uint8_t *nonce,
                                            size_t nonce_size, const uint8_t *tag, size_t tag_size,
                                            const uint8_t *ciphertext, size_t ciphertext_size,
                                            const uint8_t *associated_data,
                                            size_t associated_data_size) {
  if (context == nullptr || key_id == nullptr || key_id_size == 0 || nonce == nullptr ||
      nonce_size != 12 || tag == nullptr || tag_size != 16 || ciphertext == nullptr ||
      ciphertext_size == 0 || (associated_data == nullptr && associated_data_size != 0))
    return JOCKY_INVALID_ARGUMENT;
  context->pool.key_id.assign(key_id, key_id_size);
  context->pool.nonce.assign(nonce, nonce + nonce_size);
  context->pool.tag.assign(tag, tag + tag_size);
  context->pool.ciphertext.assign(ciphertext, ciphertext + ciphertext_size);
  context->pool.associated_data.assign(associated_data, associated_data + associated_data_size);
  return JOCKY_OK;
}

JOCKY_COLLECTOR(jocky_rt_system_info, JOCKY_OP_SYSTEM_INFO, "SYSTEM_INFO")
JOCKY_COLLECTOR(jocky_rt_users, JOCKY_OP_USER_ENUMERATE, "USER_ENUMERATE")
JOCKY_COLLECTOR(jocky_rt_processes, JOCKY_OP_PROCESS_ENUMERATE, "PROCESS_ENUMERATE")
JOCKY_COLLECTOR(jocky_rt_interfaces, JOCKY_OP_NETWORK_INTERFACE_ENUMERATE,
                "NETWORK_INTERFACE_ENUMERATE")
JOCKY_COLLECTOR(jocky_rt_connections, JOCKY_OP_NETWORK_CONNECTION_ENUMERATE,
                "NETWORK_CONNECTION_ENUMERATE")
JOCKY_COLLECTOR(jocky_rt_routes, JOCKY_OP_ROUTE_ENUMERATE, "ROUTE_ENUMERATE")
JOCKY_COLLECTOR(jocky_rt_file_metadata, JOCKY_OP_FILE_METADATA, "FILE_METADATA")
JOCKY_COLLECTOR(jocky_rt_file_hash, JOCKY_OP_FILE_HASH, "FILE_HASH")
JOCKY_COLLECTOR(jocky_rt_services, JOCKY_OP_SERVICE_ENUMERATE, "SERVICE_ENUMERATE")
JOCKY_COLLECTOR(jocky_rt_events, JOCKY_OP_EVENT_QUERY, "EVENT_QUERY")
JOCKY_COLLECTOR(jocky_rt_drivers, JOCKY_OP_DRIVER_ENUMERATE, "DRIVER_ENUMERATE")
JOCKY_COLLECTOR(jocky_rt_yara, JOCKY_OP_YARA_SCAN, "YARA_SCAN")

jocky_status jocky_rt_analysis(jocky_context *context, uint32_t instruction_id, const char *opcode,
                               size_t opcode_size, const uint8_t *config, size_t config_size,
                               const jocky_dataset_handle *inputs, size_t input_count,
                               jocky_dataset_handle *out) {
  if (opcode == nullptr || !allowed_analysis(std::string_view(opcode, opcode_size))) {
    if (out != nullptr)
      *out = JOCKY_DATASET_INVALID;
    set_error(context, JOCKY_INVALID_ARGUMENT, "OPCODE_NOT_ALLOWED",
              "The runtime accepts only compiler analysis opcodes.");
    return JOCKY_INVALID_ARGUMENT;
  }
  return dispatch(context, JOCKY_OP_ANALYSIS, instruction_id, std::string_view(opcode, opcode_size),
                  config, config_size, inputs, input_count, out);
}

jocky_status jocky_rt_fixture_context_create(jocky_context **out) {
  auto *fixture = new (std::nothrow) FixtureHost;
  if (fixture == nullptr)
    return JOCKY_INTERNAL_ERROR;
  jocky_runtime_host_v1 host{JOCKY_RUNTIME_HOST_V1,
                             sizeof(jocky_runtime_host_v1),
                             fixture,
                             fixture_invoke,
                             fixture_retain,
                             fixture_release,
                             fixture_destroy};
  auto status = jocky_rt_context_create(&host, out);
  if (status != JOCKY_OK) {
    delete fixture;
    return status;
  }
  (*out)->fixture = true;
  return JOCKY_OK;
}

int jocky_rt_fixture_is_simulation(const jocky_context *context) {
  return context != nullptr && context->fixture ? 1 : 0;
}

jocky_status jocky_rt_fixture_semantic_hash(const jocky_context *context, char *hex_out,
                                            size_t hex_out_size) {
  if (context == nullptr || !context->fixture || hex_out == nullptr || hex_out_size < 65)
    return JOCKY_INVALID_ARGUMENT;
  auto *fixture = static_cast<FixtureHost *>(context->host.user_data);
  auto value = hex_digest(fixture->trace);
  std::memcpy(hex_out, value.data(), value.size());
  hex_out[64] = '\0';
  return JOCKY_OK;
}

int jocky_rt_fixture_python_result(const jocky_context *context, size_t index, const char **name,
                                   size_t *name_size, const char **value, size_t *value_size) {
  if (!context || !context->fixture || !name || !name_size || !value || !value_size)
    return 0;
  const auto &results = static_cast<FixtureHost *>(context->host.user_data)->python_results;
  if (index >= results.size())
    return 0;
  auto entry = results.begin();
  std::advance(entry, index);
  *name = entry->first.data();
  *name_size = entry->first.size();
  *value = entry->second.data();
  *value_size = entry->second.size();
  return 1;
}
