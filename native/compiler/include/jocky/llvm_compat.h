#ifndef JOCKY_LLVM_COMPAT_H
#define JOCKY_LLVM_COMPAT_H

#include <llvm/Config/llvm-config.h>
#include <llvm/IR/Module.h>
#include <llvm/MC/TargetRegistry.h>
#include <llvm/Target/TargetMachine.h>

#include <string>

namespace jocky {

// LLVM 20 replaced the string-based triple accessors with llvm::Triple:
// Module::getTargetTriple/setTargetTriple, TargetRegistry::lookupTarget and
// Target::createTargetMachine. These shims keep one source tree building on
// LLVM 18 (the pinned CI toolchain) and on LLVM 20+ (current distro packages).

#if LLVM_VERSION_MAJOR >= 20
using TripleArgument = const llvm::Triple &;
#else
using TripleArgument = std::string;
#endif

inline TripleArgument triple_argument(const llvm::Triple &triple) {
#if LLVM_VERSION_MAJOR >= 20
  return triple;
#else
  return triple.str();
#endif
}

inline void set_module_triple(llvm::Module &module, const llvm::Triple &triple) {
  module.setTargetTriple(triple_argument(triple));
}

inline std::string module_triple(const llvm::Module &module) {
#if LLVM_VERSION_MAJOR >= 20
  return module.getTargetTriple().str();
#else
  return module.getTargetTriple();
#endif
}

} // namespace jocky

#endif
