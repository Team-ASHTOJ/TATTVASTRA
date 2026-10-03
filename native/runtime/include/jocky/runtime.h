#ifndef JOCKY_RUNTIME_H
#define JOCKY_RUNTIME_H

#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32) && defined(JOCKY_RUNTIME_BUILD)
#define JOCKY_RUNTIME_API __declspec(dllexport)
#else
#define JOCKY_RUNTIME_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define JOCKY_RUNTIME_ABI_VERSION 2u
#define JOCKY_RUNTIME_HOST_V1 1u
#define JOCKY_DATASET_INVALID ((uint64_t)0)

typedef enum jocky_status {
  JOCKY_OK = 0,
  JOCKY_UNAVAILABLE = 1,
  JOCKY_DENIED = 2,
  JOCKY_BUDGET_EXCEEDED = 3,
  JOCKY_CANCELLED = 4,
  JOCKY_INVALID_ARGUMENT = 5,
  JOCKY_INTERNAL_ERROR = 6
} jocky_status;

typedef enum jocky_operation {
  JOCKY_OP_SYSTEM_INFO = 1,
  JOCKY_OP_USER_ENUMERATE = 2,
  JOCKY_OP_PROCESS_ENUMERATE = 3,
  JOCKY_OP_NETWORK_INTERFACE_ENUMERATE = 4,
  JOCKY_OP_NETWORK_CONNECTION_ENUMERATE = 5,
  JOCKY_OP_ROUTE_ENUMERATE = 6,
  JOCKY_OP_FILE_METADATA = 7,
  JOCKY_OP_FILE_HASH = 8,
  JOCKY_OP_SERVICE_ENUMERATE = 9,
  JOCKY_OP_EVENT_QUERY = 10,
  JOCKY_OP_DRIVER_ENUMERATE = 11,
  JOCKY_OP_YARA_SCAN = 12,
  JOCKY_OP_ANALYSIS = 100
} jocky_operation;

typedef struct jocky_context jocky_context;
typedef uint64_t jocky_dataset_handle;

/* Borrowed until the next call using the context or context destruction. */
typedef struct jocky_error_view {
  jocky_status status;
  const char *code;
  size_t code_size;
  const char *message;
  size_t message_size;
} jocky_error_view;

/*
 * The host owns user_data and every dataset represented by a nonzero handle.
 * invoke creates one owned handle on success. retain/release implement explicit
 * shared ownership; no C++/Rust/STL object crosses this boundary. Config and
 * input arrays are borrowed only for the duration of invoke.
 */
typedef jocky_status (*jocky_host_invoke_fn)(void *user_data, jocky_operation operation,
                                             uint32_t instruction_id, const char *opcode,
                                             size_t opcode_size, const uint8_t *config,
                                             size_t config_size, const jocky_dataset_handle *inputs,
                                             size_t input_count, jocky_dataset_handle *out);
typedef jocky_status (*jocky_host_dataset_fn)(void *user_data, jocky_dataset_handle handle);
typedef void (*jocky_host_destroy_fn)(void *user_data);

typedef struct jocky_runtime_host_v1 {
  uint32_t host_abi_version;
  uint32_t struct_size;
  void *user_data;
  jocky_host_invoke_fn invoke;
  jocky_host_dataset_fn retain;
  jocky_host_dataset_fn release;
  jocky_host_destroy_fn destroy;
} jocky_runtime_host_v1;

JOCKY_RUNTIME_API uint32_t jocky_rt_abi_version(void);
JOCKY_RUNTIME_API jocky_status jocky_rt_context_create(const jocky_runtime_host_v1 *host,
                                                       jocky_context **out);
JOCKY_RUNTIME_API void jocky_rt_context_destroy(jocky_context *context);
JOCKY_RUNTIME_API jocky_error_view jocky_rt_last_error(const jocky_context *context);

JOCKY_RUNTIME_API jocky_status jocky_rt_dataset_retain(jocky_context *context,
                                                       jocky_dataset_handle handle);
JOCKY_RUNTIME_API jocky_status jocky_rt_dataset_release(jocky_context *context,
                                                        jocky_dataset_handle handle);

/* The runtime copies key/pool bytes. Key bytes are cleansed on replacement/destruction. */
JOCKY_RUNTIME_API jocky_status jocky_rt_set_literal_key(jocky_context *context, const char *key_id,
                                                        size_t key_id_size, const uint8_t *key,
                                                        size_t key_size);
JOCKY_RUNTIME_API jocky_status jocky_rt_register_literal_pool(
    jocky_context *context, const char *key_id, size_t key_id_size, const uint8_t *nonce,
    size_t nonce_size, const uint8_t *tag, size_t tag_size, const uint8_t *ciphertext,
    size_t ciphertext_size, const uint8_t *associated_data, size_t associated_data_size);

/* Fixed collector surface. Config is canonical compiler-generated data or null for a pool item. */
JOCKY_RUNTIME_API jocky_status jocky_rt_system_info(jocky_context *, uint32_t, const uint8_t *,
                                                    size_t, jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_users(jocky_context *, uint32_t, const uint8_t *, size_t,
                                              jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_processes(jocky_context *, uint32_t, const uint8_t *,
                                                  size_t, jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_interfaces(jocky_context *, uint32_t, const uint8_t *,
                                                   size_t, jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_connections(jocky_context *, uint32_t, const uint8_t *,
                                                    size_t, jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_routes(jocky_context *, uint32_t, const uint8_t *, size_t,
                                               jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_file_metadata(jocky_context *, uint32_t, const uint8_t *,
                                                      size_t, jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_file_hash(jocky_context *, uint32_t, const uint8_t *,
                                                  size_t, jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_services(jocky_context *, uint32_t, const uint8_t *, size_t,
                                                 jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_events(jocky_context *, uint32_t, const uint8_t *, size_t,
                                               jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_drivers(jocky_context *, uint32_t, const uint8_t *, size_t,
                                                jocky_dataset_handle *);
JOCKY_RUNTIME_API jocky_status jocky_rt_yara(jocky_context *, uint32_t, const uint8_t *, size_t,
                                             jocky_dataset_handle *);

/* Accepts only the compiler's closed analysis/evidence opcode allowlist. */
JOCKY_RUNTIME_API jocky_status jocky_rt_analysis(jocky_context *, uint32_t, const char *, size_t,
                                                 const uint8_t *, size_t,
                                                 const jocky_dataset_handle *, size_t,
                                                 jocky_dataset_handle *);

/* Deterministic test/CLI fixture. Every result is simulation=true, never REAL evidence. */
JOCKY_RUNTIME_API jocky_status jocky_rt_fixture_context_create(jocky_context **out);
/* Read-only result view; valid until the context is modified or destroyed. */
JOCKY_RUNTIME_API int jocky_rt_fixture_python_result(const jocky_context *, size_t,
                                                     const char **name, size_t *name_size,
                                                     const char **value, size_t *value_size);
JOCKY_RUNTIME_API int jocky_rt_fixture_is_simulation(const jocky_context *context);
JOCKY_RUNTIME_API jocky_status jocky_rt_fixture_semantic_hash(const jocky_context *context,
                                                              char *hex_out, size_t hex_out_size);

#ifdef __cplusplus
}
#endif
#endif
