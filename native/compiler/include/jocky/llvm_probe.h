#ifndef JOCKY_LLVM_PROBE_H
#define JOCKY_LLVM_PROBE_H
#include <string>

namespace jocky {
// Toolchain diagnostic only. This does not compile or execute a JOCKY source program.
bool verify_orc_toolchain(std::string &error);
} // namespace jocky
#endif
