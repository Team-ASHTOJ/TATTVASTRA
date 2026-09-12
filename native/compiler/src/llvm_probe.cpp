#include "jocky/llvm_probe.h"
#include "jocky/runtime.h"
#include <llvm/ExecutionEngine/Orc/LLJIT.h>
#include <llvm/IR/IRBuilder.h>
#include <llvm/IR/Module.h>
#include <llvm/IR/Verifier.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/TargetSelect.h>

namespace jocky {
bool verify_orc_toolchain(std::string &error) {
  if (llvm::InitializeNativeTarget() || llvm::InitializeNativeTargetAsmPrinter()) {
    error = "Native LLVM target initialization failed";
    return false;
  }
  auto jit = llvm::orc::LLJITBuilder().create();
  if (!jit) {
    error = llvm::toString(jit.takeError());
    return false;
  }
  auto context = std::make_unique<llvm::LLVMContext>();
  auto module = std::make_unique<llvm::Module>("jocky_toolchain_probe", *context);
  module->setDataLayout((*jit)->getDataLayout());
  module->setTargetTriple((*jit)->getTargetTriple().str());
  llvm::IRBuilder<> builder(*context);
  auto *type = llvm::FunctionType::get(builder.getInt32Ty(), false);
  auto *function =
      llvm::Function::Create(type, llvm::Function::ExternalLinkage, "jocky_probe_abi", *module);
  builder.SetInsertPoint(llvm::BasicBlock::Create(*context, "entry", function));
  builder.CreateRet(builder.getInt32(JOCKY_RUNTIME_ABI_VERSION));
  if (llvm::verifyModule(*module, &llvm::errs())) {
    error = "Toolchain probe generated invalid LLVM IR";
    return false;
  }
  if (auto failure =
          (*jit)->addIRModule(llvm::orc::ThreadSafeModule(std::move(module), std::move(context)))) {
    error = llvm::toString(std::move(failure));
    return false;
  }
  auto symbol = (*jit)->lookup("jocky_probe_abi");
  if (!symbol) {
    error = llvm::toString(symbol.takeError());
    return false;
  }
  auto probe = symbol->toPtr<uint32_t (*)()>();
  if (probe() != jocky_rt_abi_version()) {
    error = "ORC machine code result does not match runtime ABI version";
    return false;
  }
  return true;
}
} // namespace jocky
