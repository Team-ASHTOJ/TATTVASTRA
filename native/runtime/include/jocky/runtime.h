#ifndef JOCKY_RUNTIME_H
#define JOCKY_RUNTIME_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define JOCKY_RUNTIME_ABI_VERSION 1u

typedef enum jocky_status {
  JOCKY_OK = 0,
  JOCKY_UNAVAILABLE = 1,
  JOCKY_DENIED = 2,
  JOCKY_BUDGET_EXCEEDED = 3,
  JOCKY_CANCELLED = 4,
  JOCKY_INVALID_ARGUMENT = 5,
  JOCKY_INTERNAL_ERROR = 6
} jocky_status;

/* Owned by the Rust runtime host. No raw arbitrary process or payload API. */
typedef struct jocky_context jocky_context;
typedef uint64_t jocky_dataset_handle;

uint32_t jocky_rt_abi_version(void);
jocky_status jocky_rt_system_info(jocky_context *context, jocky_dataset_handle *out);
jocky_status jocky_rt_process_list(jocky_context *context, jocky_dataset_handle *out);
jocky_status jocky_rt_network_connections(jocky_context *context, jocky_dataset_handle *out);
jocky_status jocky_rt_file_metadata(jocky_context *context, const char *path, size_t path_size,
                                    jocky_dataset_handle *out);
jocky_status jocky_rt_file_hash(jocky_context *context, const char *path, size_t path_size,
                                jocky_dataset_handle *out);
jocky_status jocky_rt_services(jocky_context *context, jocky_dataset_handle *out);
jocky_status jocky_rt_users(jocky_context *context, jocky_dataset_handle *out);
jocky_status jocky_rt_events(jocky_context *context, jocky_dataset_handle *out);
jocky_status jocky_rt_drivers(jocky_context *context, jocky_dataset_handle *out);

#ifdef __cplusplus
}
#endif
#endif
