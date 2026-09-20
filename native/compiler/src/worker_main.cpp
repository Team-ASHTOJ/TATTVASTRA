#include "jocky/worker.h"
#include <llvm/ExecutionEngine/Orc/LLJIT.h>
#include <llvm/ExecutionEngine/Orc/Mangling.h>
#include <llvm/Support/MemoryBuffer.h>
#include <llvm/Support/TargetSelect.h>
#include <llvm/Support/raw_ostream.h>
#include <string>

int main(int argc, char **argv) {
  if (argc != 3)
    return 64;
  std::string entry(argv[2]);
  if (entry.size() != 28 || entry.substr(0, 12) != "jocky_entry_" ||
      entry.find_first_not_of("0123456789abcdef", 12) != std::string::npos)
    return 64;
  llvm::InitializeNativeTarget();
  llvm::InitializeNativeTargetAsmPrinter();
  auto jit = llvm::orc::LLJITBuilder().create();
  if (!jit) {
    llvm::consumeError(jit.takeError());
    return 70;
  }
  llvm::orc::MangleAndInterner mangle((*jit)->getExecutionSession(), (*jit)->getDataLayout());
  llvm::orc::SymbolMap symbols;
  // Deliberately no process-wide symbol resolver: compiled programs only receive
  // the versioned runtime C ABI, never libc/process/network entry points.
#define JOCKY_BIND(name)                                                                           \
  symbols[mangle(#name)] = {llvm::orc::ExecutorAddr::fromPtr(&name), llvm::JITSymbolFlags::Exported}
  JOCKY_BIND(jocky_rt_abi_version);
  JOCKY_BIND(jocky_rt_dataset_retain);
  JOCKY_BIND(jocky_rt_dataset_release);
  JOCKY_BIND(jocky_rt_system_info);
  JOCKY_BIND(jocky_rt_users);
  JOCKY_BIND(jocky_rt_processes);
  JOCKY_BIND(jocky_rt_interfaces);
  JOCKY_BIND(jocky_rt_connections);
  JOCKY_BIND(jocky_rt_routes);
  JOCKY_BIND(jocky_rt_file_metadata);
  JOCKY_BIND(jocky_rt_file_hash);
  JOCKY_BIND(jocky_rt_services);
  JOCKY_BIND(jocky_rt_events);
  JOCKY_BIND(jocky_rt_drivers);
  JOCKY_BIND(jocky_rt_analysis);
  JOCKY_BIND(jocky_rt_register_literal_pool);
#undef JOCKY_BIND
  if (auto error = (*jit)->getMainJITDylib().define(llvm::orc::absoluteSymbols(symbols))) {
    llvm::consumeError(std::move(error));
    return 70;
  }
  auto object = llvm::MemoryBuffer::getFile(argv[1]);
  if (!object)
    return 66;
  if (auto error = (*jit)->addObjectFile(std::move(*object))) {
    llvm::consumeError(std::move(error));
    return 70;
  }
  auto symbol = (*jit)->lookup(entry);
  if (!symbol) {
    llvm::consumeError(symbol.takeError());
    return 70;
  }
  return jocky_worker_run(symbol->toPtr<uint32_t (*)(jocky_context *)>());
}
