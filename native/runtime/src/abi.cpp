#include "jocky/runtime.h"

namespace {
jocky_status unavailable(jocky_context *context, jocky_dataset_handle *out) {
  if (out == nullptr) {
    return JOCKY_INVALID_ARGUMENT;
  }
  *out = 0;
  return context == nullptr ? JOCKY_INVALID_ARGUMENT : JOCKY_UNAVAILABLE;
}
} // namespace

uint32_t jocky_rt_abi_version(void) { return JOCKY_RUNTIME_ABI_VERSION; }

// The ABI boundary exists; collector implementations are a separately tracked phase.
jocky_status jocky_rt_system_info(jocky_context *context, jocky_dataset_handle *out) {
  return unavailable(context, out);
}
jocky_status jocky_rt_process_list(jocky_context *context, jocky_dataset_handle *out) {
  return unavailable(context, out);
}
jocky_status jocky_rt_network_connections(jocky_context *context, jocky_dataset_handle *out) {
  return unavailable(context, out);
}
jocky_status jocky_rt_file_metadata(jocky_context *context, const char *, size_t,
                                    jocky_dataset_handle *out) {
  return unavailable(context, out);
}
jocky_status jocky_rt_file_hash(jocky_context *context, const char *, size_t,
                                jocky_dataset_handle *out) {
  return unavailable(context, out);
}
jocky_status jocky_rt_services(jocky_context *context, jocky_dataset_handle *out) {
  return unavailable(context, out);
}
jocky_status jocky_rt_users(jocky_context *context, jocky_dataset_handle *out) {
  return unavailable(context, out);
}
jocky_status jocky_rt_events(jocky_context *context, jocky_dataset_handle *out) {
  return unavailable(context, out);
}
jocky_status jocky_rt_drivers(jocky_context *context, jocky_dataset_handle *out) {
  return unavailable(context, out);
}
