#include "jocky/llvm_probe.h"
#include <iostream>
#include <llvm/Config/llvm-config.h>
#include <string>

int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--version") {
    std::cout << "jockyc 0.1.0 (foundation; LLVM " << LLVM_VERSION_STRING << ")\n";
    return 0;
  }
  if (argc == 2 && std::string(argv[1]) == "--self-test") {
    std::string error;
    if (!jocky::verify_orc_toolchain(error)) {
      std::cerr << "JOCKY_E_LLVM_TOOLCHAIN: " << error << '\n';
      return 70;
    }
    std::cout << "PASS: real LLVM ORC toolchain probe; JOCKY frontend is unavailable\n";
    return 0;
  }
  if (argc == 2 && std::string(argv[1]) == "--help") {
    std::cout << "jockyc --version | --self-test\n"
                 "Planned: check ast jir llvm plan compile variants run benchmark <file.jky>\n"
                 "Source commands are unavailable in the foundation release.\n";
    return 0;
  }
  std::cerr << "JOCKY_E_FRONTEND_UNAVAILABLE: JOCKY source compilation/execution is not "
               "implemented. See docs/BUILD_STATUS.md phases P1-P3.\n";
  return 69;
}
