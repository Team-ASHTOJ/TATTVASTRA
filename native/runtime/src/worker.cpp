#include "jocky/worker.h"
#include <iostream>
#include <string>

namespace {
jocky_status invoke(void *, jocky_operation operation, uint32_t instruction, const char *opcode,
                    size_t opcode_size, const uint8_t *config, size_t config_size,
                    const jocky_dataset_handle *inputs, size_t input_count,
                    jocky_dataset_handle *out) {
  // Opcode is drawn from the runtime's closed registry. Config is canonical JSON
  // emitted by the compiler; no user string is interpolated as executable code.
  std::cout << "{\"operation\":" << operation << ",\"instruction\":" << instruction
            << ",\"opcode\":\"" << std::string(opcode, opcode_size) << "\",\"config\":";
  if (config_size)
    std::cout.write(reinterpret_cast<const char *>(config), config_size);
  else
    std::cout << "{}";
  std::cout << ",\"inputs\":[";
  for (size_t i = 0; i < input_count; ++i) {
    if (i)
      std::cout << ',';
    std::cout << inputs[i];
  }
  std::cout << "]}" << std::endl;
  unsigned status = JOCKY_INTERNAL_ERROR;
  uint64_t handle = 0;
  if (!(std::cin >> status >> handle) || status > JOCKY_INTERNAL_ERROR)
    return JOCKY_INTERNAL_ERROR;
  *out = handle;
  return static_cast<jocky_status>(status);
}
jocky_status dataset(void *, jocky_dataset_handle) { return JOCKY_OK; }
} // namespace

int jocky_worker_run(uint32_t (*entry)(jocky_context *)) {
  jocky_runtime_host_v1 host{JOCKY_RUNTIME_HOST_V1,
                             sizeof(jocky_runtime_host_v1),
                             nullptr,
                             invoke,
                             dataset,
                             dataset,
                             nullptr};
  jocky_context *context = nullptr;
  auto status = jocky_rt_context_create(&host, &context);
  if (status != JOCKY_OK)
    return static_cast<int>(status);
  status = static_cast<jocky_status>(entry(context));
  jocky_rt_context_destroy(context);
  return static_cast<int>(status);
}
