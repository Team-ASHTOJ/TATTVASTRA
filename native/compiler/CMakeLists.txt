llvm_map_components_to_libnames(JOCKY_LLVM_COMPONENTS
  Core Support OrcJIT ExecutionEngine native Target Passes Analysis TransformUtils CodeGen MC)
# Not every distribution ships the static component archives (Arch provides only
# libLLVM.so). LLVMConfig reports that layout through LLVM_LINK_LLVM_DYLIB.
if(LLVM_LINK_LLVM_DYLIB)
  set(JOCKY_LLVM_LIBS LLVM)
else()
  set(JOCKY_LLVM_LIBS ${JOCKY_LLVM_COMPONENTS})
endif()
add_library(jocky_llvm_probe STATIC src/llvm_probe.cpp)
target_include_directories(jocky_llvm_probe PUBLIC include)
target_include_directories(jocky_llvm_probe SYSTEM PRIVATE ${LLVM_INCLUDE_DIRS})
separate_arguments(JOCKY_LLVM_DEFINITIONS NATIVE_COMMAND "${LLVM_DEFINITIONS}")
target_compile_options(jocky_llvm_probe PRIVATE ${JOCKY_LLVM_DEFINITIONS})
target_link_libraries(jocky_llvm_probe PUBLIC ${JOCKY_LLVM_LIBS} jocky_runtime)

add_library(jocky_frontend STATIC
  src/source.cpp src/lexer.cpp src/parser.cpp src/ast.cpp src/types.cpp
  src/registry.cpp src/jir.cpp src/semantic.cpp src/configuration.cpp
  src/expressions.cpp src/collect.cpp src/queries.cpp src/investigation.cpp
  src/literal_pool.cpp src/backend.cpp)
target_include_directories(jocky_frontend PUBLIC include)
target_include_directories(jocky_frontend SYSTEM PUBLIC ${LLVM_INCLUDE_DIRS})
target_compile_options(jocky_frontend PRIVATE -Wall -Wextra -Wpedantic -Werror)
target_link_libraries(jocky_frontend PUBLIC ${JOCKY_LLVM_LIBS} jocky_runtime)

add_executable(jockyc src/main.cpp)
target_include_directories(jockyc SYSTEM PRIVATE ${LLVM_INCLUDE_DIRS})
target_link_libraries(jockyc PRIVATE jocky_llvm_probe jocky_frontend)
set_target_properties(jockyc PROPERTIES ENABLE_EXPORTS ON)
install(TARGETS jockyc RUNTIME DESTINATION bin)
add_executable(jocky-worker src/worker_main.cpp)
target_include_directories(jocky-worker SYSTEM PRIVATE ${LLVM_INCLUDE_DIRS})
target_link_libraries(jocky-worker PRIVATE ${JOCKY_LLVM_LIBS} jocky_worker_host)
install(TARGETS jocky-worker RUNTIME DESTINATION bin)

if(BUILD_TESTING)
  add_executable(compiler_tests tests/llvm_probe_test.cpp)
  target_link_libraries(compiler_tests PRIVATE jocky_llvm_probe GTest::gtest_main)
  gtest_discover_tests(compiler_tests)
  add_executable(frontend_tests tests/frontend_test.cpp)
  target_link_libraries(frontend_tests PRIVATE jocky_frontend GTest::gtest_main)
  gtest_discover_tests(frontend_tests)
  add_executable(backend_tests tests/backend_test.cpp)
  target_link_libraries(backend_tests PRIVATE jocky_frontend jocky_runtime GTest::gtest_main)
  set_target_properties(backend_tests PROPERTIES ENABLE_EXPORTS ON)
  gtest_discover_tests(backend_tests)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  add_test(NAME frontend_examples_and_goldens
    COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/scripts/test_frontend.py
            --compiler $<TARGET_FILE:jockyc>)
  add_test(NAME cross_target_objects_and_rejections
    COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/scripts/test_cross_target.py
            --compiler $<TARGET_FILE:jockyc>)
  add_test(NAME compiler_rejects_missing_source COMMAND jockyc check missing.jky)
  set_tests_properties(compiler_rejects_missing_source PROPERTIES WILL_FAIL TRUE)
endif()

if(BUILD_TESTING)
  add_test(NAME python_interop
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/python_interop_test.py
            $<TARGET_FILE:jockyc>)
endif()
