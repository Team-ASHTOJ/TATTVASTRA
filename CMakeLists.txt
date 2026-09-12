cmake_minimum_required(VERSION 3.25)
project(JOCKY VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# LLVM is mandatory. Never add a mock/no-LLVM compiler configuration.
find_package(LLVM REQUIRED CONFIG)
if(LLVM_PACKAGE_VERSION VERSION_LESS 18)
  message(FATAL_ERROR "JOCKY requires LLVM >= 18; reference CI uses LLVM 18")
endif()
message(STATUS "JOCKY LLVM ${LLVM_PACKAGE_VERSION}: ${LLVM_DIR}")

include(CTest)
if(BUILD_TESTING)
  find_package(GTest REQUIRED CONFIG)
  include(GoogleTest)
endif()

add_subdirectory(native/runtime)
add_subdirectory(native/compiler)
