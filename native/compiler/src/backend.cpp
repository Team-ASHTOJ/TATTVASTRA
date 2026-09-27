#include "jocky/backend.h"

#include <algorithm>
#include <chrono>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <llvm/Config/llvm-config.h>
#include <llvm/ExecutionEngine/Orc/ExecutionUtils.h>
#include <llvm/ExecutionEngine/Orc/LLJIT.h>
#include <llvm/IR/Attributes.h>
#include <llvm/IR/IRBuilder.h>
#include <llvm/IR/LegacyPassManager.h>
#include <llvm/IR/Verifier.h>
#include <llvm/MC/TargetRegistry.h>
#include <llvm/Passes/OptimizationLevel.h>
#include <llvm/Passes/PassBuilder.h>
#include <llvm/Support/FileSystem.h>
#include <llvm/Support/TargetSelect.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/Target/TargetMachine.h>
#include <llvm/TargetParser/Host.h>
#include <llvm/Transforms/Utils/Cloning.h>
#include <numeric>
#include <sstream>

namespace jocky {
namespace {
using Clock = std::chrono::steady_clock;

double elapsed_ms(Clock::time_point start) {
  return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

uint64_t deterministic_next(uint64_t &state) {
  state += 0x9e3779b97f4a7c15ULL;
  uint64_t value = state;
  value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;
  value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;
  return value ^ (value >> 31U);
}

std::string seed_hex(uint64_t seed) {
  std::ostringstream output;
  output << std::hex << std::setw(16) << std::setfill('0') << seed;
  return output.str();
}

std::string bytes_hex(const uint8_t *data, size_t size) {
  static constexpr char hex[] = "0123456789abcdef";
  std::string output(size * 2, '0');
  for (size_t index = 0; index < size; ++index) {
    output[index * 2] = hex[data[index] >> 4U];
    output[index * 2 + 1] = hex[data[index] & 15U];
  }
  return output;
}

std::unique_ptr<llvm::TargetMachine> target_machine(std::string &error,
                                                    const std::string &requested = "host") {
  static const bool initialized = [] {
    LLVMInitializeX86TargetInfo();
    LLVMInitializeX86Target();
    LLVMInitializeX86TargetMC();
    LLVMInitializeX86AsmPrinter();
    LLVMInitializeX86AsmParser();
    LLVMInitializeAArch64TargetInfo();
    LLVMInitializeAArch64Target();
    LLVMInitializeAArch64TargetMC();
    LLVMInitializeAArch64AsmPrinter();
    LLVMInitializeAArch64AsmParser();
    return true;
  }();
  (void)initialized;
  auto name = requested == "host" ? llvm::sys::getDefaultTargetTriple() : requested;
  if (name == "linux-x86_64")
    name = "x86_64-unknown-linux-gnu";
  if (name == "linux-aarch64")
    name = "aarch64-unknown-linux-gnu";
  if (name == "windows-x86_64")
    name = "x86_64-pc-windows-msvc";
  llvm::Triple triple(name);
  const auto *target = llvm::TargetRegistry::lookupTarget(triple.str(), error);
  if (target == nullptr)
    return nullptr;
  llvm::TargetOptions options;
  return std::unique_ptr<llvm::TargetMachine>(
      target->createTargetMachine(triple.str(), "generic", "", options, llvm::Reloc::PIC_,
                                  std::nullopt, llvm::CodeGenOptLevel::Default));
}

llvm::GlobalVariable *byte_global(llvm::Module &module, llvm::StringRef name, const uint8_t *data,
                                  size_t size, bool externally_visible = false) {
  auto &context = module.getContext();
  auto *type = llvm::ArrayType::get(llvm::Type::getInt8Ty(context), size);
  auto value = llvm::ConstantDataArray::get(
      context, llvm::ArrayRef<uint8_t>(data, static_cast<size_t>(size)));
  auto linkage =
      externally_visible ? llvm::GlobalValue::ExternalLinkage : llvm::GlobalValue::PrivateLinkage;
  auto *global = new llvm::GlobalVariable(module, type, true, linkage, value, name);
  global->setUnnamedAddr(externally_visible ? llvm::GlobalValue::UnnamedAddr::None
                                            : llvm::GlobalValue::UnnamedAddr::Global);
  return global;
}

llvm::GlobalVariable *string_global(llvm::Module &module, llvm::StringRef name,
                                    const std::string &value, bool externally_visible = false) {
  return byte_global(module, name, reinterpret_cast<const uint8_t *>(value.data()), value.size(),
                     externally_visible);
}

llvm::FunctionCallee collector_declaration(llvm::Module &module, llvm::StringRef name) {
  auto &context = module.getContext();
  auto *pointer = llvm::PointerType::getUnqual(context);
  auto *type = llvm::FunctionType::get(
      llvm::Type::getInt32Ty(context),
      {pointer, llvm::Type::getInt32Ty(context), pointer, llvm::Type::getInt64Ty(context), pointer},
      false);
  return module.getOrInsertFunction(name, type);
}

llvm::FunctionCallee analysis_declaration(llvm::Module &module) {
  auto &context = module.getContext();
  auto *pointer = llvm::PointerType::getUnqual(context);
  auto *type = llvm::FunctionType::get(
      llvm::Type::getInt32Ty(context),
      {pointer, llvm::Type::getInt32Ty(context), pointer, llvm::Type::getInt64Ty(context), pointer,
       llvm::Type::getInt64Ty(context), pointer, llvm::Type::getInt64Ty(context), pointer},
      false);
  return module.getOrInsertFunction("jocky_rt_analysis", type);
}

std::string collector_symbol(const std::string &opcode) {
  static const std::map<std::string, std::string> symbols{
      {"SYSTEM_INFO", "jocky_rt_system_info"},
      {"USER_ENUMERATE", "jocky_rt_users"},
      {"PROCESS_ENUMERATE", "jocky_rt_processes"},
      {"NETWORK_INTERFACE_ENUMERATE", "jocky_rt_interfaces"},
      {"NETWORK_CONNECTION_ENUMERATE", "jocky_rt_connections"},
      {"ROUTE_ENUMERATE", "jocky_rt_routes"},
      {"FILE_METADATA", "jocky_rt_file_metadata"},
      {"FILE_HASH", "jocky_rt_file_hash"},
      {"SERVICE_ENUMERATE", "jocky_rt_services"},
      {"EVENT_QUERY", "jocky_rt_events"},
      {"DRIVER_ENUMERATE", "jocky_rt_drivers"}};
  auto found = symbols.find(opcode);
  return found == symbols.end() ? std::string{} : found->second;
}

llvm::Function *create_helper(llvm::Module &module, const Instruction &instruction,
                              uint32_t strategy, const std::string &name, bool protected_literals) {
  auto &context = module.getContext();
  llvm::IRBuilder<> builder(context);
  auto *pointer = llvm::PointerType::getUnqual(context);
  auto *type = llvm::FunctionType::get(llvm::Type::getInt32Ty(context), {pointer, pointer}, false);
  auto *function = llvm::Function::Create(type, llvm::Function::InternalLinkage, name, module);
  function->addFnAttr(llvm::Attribute::NoInline);
  function->addFnAttr(llvm::Attribute::OptimizeNone);
  auto args = function->arg_begin();
  llvm::Value *runtime = &*args++;
  llvm::Value *handles = &*args;
  runtime->setName("runtime");
  handles->setName("handles");
  auto *entry = llvm::BasicBlock::Create(context, "entry", function);
  builder.SetInsertPoint(entry);
  llvm::Value *config = llvm::ConstantPointerNull::get(pointer);
  uint64_t config_size = 0;
  if (!protected_literals) {
    auto value = canonical_json(llvm::json::Value(llvm::json::Object(instruction.attributes)));
    auto *global = string_global(module, name + ".config", value);
    config = global;
    config_size = value.size();
  }
  auto collector = collector_symbol(instruction.opcode);
  if (collector.empty() && opcodes().at(instruction.opcode).effect == "read") {
    fail("E260",
         "LLVM lowering is not implemented for collector opcode `" + instruction.opcode + "`.",
         instruction.span);
  }
  auto *opcode_global =
      collector.empty() ? string_global(module, name + ".opcode", instruction.opcode) : nullptr;
  auto emit_call = [&](llvm::IRBuilder<> &call_builder) -> llvm::Value * {
    auto *out = call_builder.CreateInBoundsGEP(
        call_builder.getInt64Ty(), handles, call_builder.getInt64(instruction.id), "result.slot");
    if (!collector.empty())
      return call_builder.CreateCall(collector_declaration(module, collector),
                                     {runtime,
                                      call_builder.getInt32(static_cast<uint32_t>(instruction.id)),
                                      config, call_builder.getInt64(config_size), out});
    llvm::Value *input_pointer = llvm::ConstantPointerNull::get(pointer);
    if (!instruction.inputs.empty()) {
      auto *input_array = call_builder.CreateAlloca(
          call_builder.getInt64Ty(), call_builder.getInt64(instruction.inputs.size()), "inputs");
      for (size_t index = 0; index < instruction.inputs.size(); ++index) {
        auto *source = call_builder.CreateInBoundsGEP(
            call_builder.getInt64Ty(), handles, call_builder.getInt64(instruction.inputs[index]));
        auto *target = call_builder.CreateInBoundsGEP(call_builder.getInt64Ty(), input_array,
                                                      call_builder.getInt64(index));
        call_builder.CreateStore(call_builder.CreateLoad(call_builder.getInt64Ty(), source),
                                 target);
      }
      input_pointer = input_array;
    }
    return call_builder.CreateCall(analysis_declaration(module),
                                   {runtime,
                                    call_builder.getInt32(static_cast<uint32_t>(instruction.id)),
                                    opcode_global, call_builder.getInt64(instruction.opcode.size()),
                                    config, call_builder.getInt64(config_size), input_pointer,
                                    call_builder.getInt64(instruction.inputs.size()), out});
  };
  if (strategy == 0) {
    builder.CreateRet(emit_call(builder));
  } else {
    const uint32_t arms = strategy + 1;
    auto *selector = builder.CreateURem(builder.CreatePtrToInt(runtime, builder.getInt64Ty()),
                                        builder.getInt64(arms), "layout.selector");
    std::vector<llvm::BasicBlock *> blocks;
    for (uint32_t arm = 0; arm < arms; ++arm)
      blocks.push_back(
          llvm::BasicBlock::Create(context, "layout." + std::to_string(arm), function));
    auto *dispatch = builder.CreateSwitch(selector, blocks.back(), arms - 1);
    for (uint32_t arm = 0; arm + 1 < arms; ++arm)
      dispatch->addCase(builder.getInt64(arm), blocks[arm]);
    for (uint32_t arm = 0; arm < blocks.size(); ++arm) {
      auto *marker = new llvm::GlobalVariable(
          module, builder.getInt64Ty(), true, llvm::GlobalValue::PrivateLinkage,
          builder.getInt64((static_cast<uint64_t>(strategy) << 32U) | arm),
          name + ".layout.marker." + std::to_string(arm));
      marker->setUnnamedAddr(llvm::GlobalValue::UnnamedAddr::Global);
      auto *block = blocks[arm];
      builder.SetInsertPoint(block);
      builder.CreateLoad(builder.getInt64Ty(), marker, true, "layout.marker");
      builder.CreateRet(emit_call(builder));
    }
  }
  return function;
}

void optimize(llvm::Module &module) {
  llvm::LoopAnalysisManager loops;
  llvm::FunctionAnalysisManager functions;
  llvm::CGSCCAnalysisManager cgscc;
  llvm::ModuleAnalysisManager modules;
  llvm::PassBuilder passes;
  passes.registerModuleAnalyses(modules);
  passes.registerCGSCCAnalyses(cgscc);
  passes.registerFunctionAnalyses(functions);
  passes.registerLoopAnalyses(loops);
  passes.crossRegisterProxies(loops, functions, cgscc, modules);
  auto pipeline = passes.buildPerModuleDefaultPipeline(llvm::OptimizationLevel::O2);
  pipeline.run(module, modules);
}

StructuralMetrics structural_metrics(const llvm::Module &module, std::vector<uint32_t> strategies,
                                     uint64_t helper_count) {
  StructuralMetrics result;
  result.function_count = std::distance(module.begin(), module.end());
  for (const auto &function : module)
    result.basic_block_count += function.size();
  result.generated_helper_count = helper_count;
  result.lowering_strategy_ids = std::move(strategies);
  llvm::json::Array strategy_json;
  for (auto strategy : result.lowering_strategy_ids)
    strategy_json.push_back(static_cast<int64_t>(strategy));
  result.fingerprint = sha256(canonical_json(llvm::json::Object{
      {"basic_block_count", static_cast<int64_t>(result.basic_block_count)},
      {"function_count", static_cast<int64_t>(result.function_count)},
      {"generated_helper_count", static_cast<int64_t>(result.generated_helper_count)},
      {"lowering_strategy_ids", std::move(strategy_json)}}));
  return result;
}

std::string file_sha256(const std::string &path) {
  std::ifstream input(path, std::ios::binary);
  if (!input)
    fail("E264", "Cannot read emitted artifact for hashing.", {});
  std::ostringstream bytes;
  bytes << input.rdbuf();
  return sha256(bytes.str());
}

std::optional<std::string> optional_string(const llvm::json::Object &object, llvm::StringRef key) {
  if (auto value = object.getString(key))
    return value->str();
  return std::nullopt;
}
} // namespace

std::string utc_now() {
  auto now = std::chrono::system_clock::now();
  auto time = std::chrono::system_clock::to_time_t(now);
  std::tm utc{};
#ifdef _WIN32
  gmtime_s(&utc, &time);
#else
  gmtime_r(&time, &utc);
#endif
  std::ostringstream output;
  output << std::put_time(&utc, "%Y-%m-%dT%H:%M:%SZ");
  return output.str();
}

LoweredVariant lower_to_llvm(const FrontendModule &frontend, const VariantOptions &options) {
  validate_jir(frontend);
  LoweredVariant result;
  auto variant_start = Clock::now();
  auto jir_bytes = canonical_json(jir_json(frontend));
  auto jir_hash = sha256(jir_bytes);
  auto seed = seed_hex(options.seed);
  std::string target_error;
  auto machine = target_machine(target_error, options.target_triple);
  if (machine == nullptr)
    fail("E263", "LLVM target is unavailable: " + target_error, {});
  auto identity = frontend.source_hash + ":" + jir_hash + ":" + compiler_version + ":" + seed +
                  ":" + options.profile + ":" + options.execution_mode + ":" +
                  machine->getTargetTriple().str();
  auto variant_id = sha256(identity);
  result.profile.variant_ms = elapsed_ms(variant_start);

  auto llvm_start = Clock::now();
  result.context = std::make_unique<llvm::LLVMContext>();
  result.module =
      std::make_unique<llvm::Module>("jocky_variant_" + variant_id.substr(0, 16), *result.context);
  result.module->setTargetTriple(machine->getTargetTriple().str());
  result.module->setDataLayout(machine->createDataLayout());
  string_global(*result.module, "jocky_variant_identity_" + variant_id.substr(0, 16), identity,
                true);

  std::vector<size_t> helper_order(frontend.instructions.size());
  std::iota(helper_order.begin(), helper_order.end(), 0);
  uint64_t diversity_state = options.seed;
  for (size_t size = helper_order.size(); size > 1; --size) {
    auto selected = static_cast<size_t>(deterministic_next(diversity_state) % size);
    std::swap(helper_order[size - 1], helper_order[selected]);
  }
  std::vector<uint32_t> strategies(frontend.instructions.size());
  std::vector<llvm::Function *> helpers(frontend.instructions.size());
  for (auto index : helper_order) {
    auto limit = options.profile == "minimal" ? 2U : 3U;
    auto strategy = static_cast<uint32_t>(deterministic_next(diversity_state) % limit);
    strategies[index] = strategy;
    auto suffix = sha256(variant_id + ":" + std::to_string(index)).substr(0, 12);
    helpers[index] = create_helper(*result.module, frontend.instructions[index], strategy,
                                   "jocky_h_" + suffix, options.protect_literals);
  }

  result.entry_symbol = "jocky_entry_" + variant_id.substr(0, 16);
  llvm::IRBuilder<> builder(*result.context);
  auto *pointer = llvm::PointerType::getUnqual(*result.context);
  auto *entry_type = llvm::FunctionType::get(builder.getInt32Ty(), {pointer}, false);
  auto *entry = llvm::Function::Create(entry_type, llvm::Function::ExternalLinkage,
                                       result.entry_symbol, *result.module);
  entry->addFnAttr(llvm::Attribute::NoInline);
  auto *entry_block = llvm::BasicBlock::Create(*result.context, "entry", entry);
  auto *cleanup = llvm::BasicBlock::Create(*result.context, "cleanup", entry);
  builder.SetInsertPoint(entry_block);
  llvm::Value *runtime = &*entry->arg_begin();
  auto slot_count = std::max<size_t>(1, frontend.instructions.size());
  auto *handles =
      builder.CreateAlloca(builder.getInt64Ty(), builder.getInt64(slot_count), "handles");
  for (size_t index = 0; index < slot_count; ++index) {
    auto *slot = builder.CreateInBoundsGEP(builder.getInt64Ty(), handles, builder.getInt64(index));
    builder.CreateStore(builder.getInt64(0), slot);
  }
  auto *status_slot = builder.CreateAlloca(builder.getInt32Ty(), nullptr, "status");
  builder.CreateStore(builder.getInt32(JOCKY_OK), status_slot);

  std::optional<ProtectedLiteralPool> pool;
  if (options.protect_literals) {
    auto aad = "JOCKY:literal-pool:v1\n" + frontend.source_hash + ":" + jir_hash + ":" + variant_id;
    pool = protect_literal_pool(frontend, options.literal_key, options.literal_key_id, aad);
    auto *key_id = string_global(*result.module, "jocky.literal.key_id", pool->key_id);
    auto *nonce =
        byte_global(*result.module, "jocky.literal.nonce", pool->nonce.data(), pool->nonce.size());
    auto *tag =
        byte_global(*result.module, "jocky.literal.tag", pool->tag.data(), pool->tag.size());
    auto *ciphertext = byte_global(*result.module, "jocky.literal.ciphertext",
                                   pool->ciphertext.data(), pool->ciphertext.size());
    auto *aad_global = string_global(*result.module, "jocky.literal.aad", pool->associated_data);
    auto *register_type = llvm::FunctionType::get(
        builder.getInt32Ty(),
        {pointer, pointer, builder.getInt64Ty(), pointer, builder.getInt64Ty(), pointer,
         builder.getInt64Ty(), pointer, builder.getInt64Ty(), pointer, builder.getInt64Ty()},
        false);
    auto register_pool =
        result.module->getOrInsertFunction("jocky_rt_register_literal_pool", register_type);
    auto *status =
        builder.CreateCall(register_pool, {runtime, key_id, builder.getInt64(pool->key_id.size()),
                                           nonce, builder.getInt64(pool->nonce.size()), tag,
                                           builder.getInt64(pool->tag.size()), ciphertext,
                                           builder.getInt64(pool->ciphertext.size()), aad_global,
                                           builder.getInt64(pool->associated_data.size())});
    auto *ready = llvm::BasicBlock::Create(*result.context, "pool.ready", entry);
    auto *failed = llvm::BasicBlock::Create(*result.context, "pool.failed", entry);
    builder.CreateCondBr(builder.CreateICmpEQ(status, builder.getInt32(JOCKY_OK)), ready, failed);
    builder.SetInsertPoint(failed);
    builder.CreateStore(status, status_slot);
    builder.CreateBr(cleanup);
    builder.SetInsertPoint(ready);
  }

  for (size_t index = 0; index < helpers.size(); ++index) {
    auto *status = builder.CreateCall(helpers[index], {runtime, handles});
    auto *next = llvm::BasicBlock::Create(*result.context,
                                          "instruction." + std::to_string(index) + ".ok", entry);
    auto *failed = llvm::BasicBlock::Create(
        *result.context, "instruction." + std::to_string(index) + ".failed", entry);
    builder.CreateCondBr(builder.CreateICmpEQ(status, builder.getInt32(JOCKY_OK)), next, failed);
    builder.SetInsertPoint(failed);
    builder.CreateStore(status, status_slot);
    builder.CreateBr(cleanup);
    builder.SetInsertPoint(next);
  }
  builder.CreateBr(cleanup);
  builder.SetInsertPoint(cleanup);
  auto *release_type =
      llvm::FunctionType::get(builder.getInt32Ty(), {pointer, builder.getInt64Ty()}, false);
  auto release = result.module->getOrInsertFunction("jocky_rt_dataset_release", release_type);
  for (size_t index = 0; index < frontend.instructions.size(); ++index) {
    auto *slot = builder.CreateInBoundsGEP(builder.getInt64Ty(), handles, builder.getInt64(index));
    builder.CreateCall(release, {runtime, builder.CreateLoad(builder.getInt64Ty(), slot)});
  }
  builder.CreateRet(builder.CreateLoad(builder.getInt32Ty(), status_slot));
  result.profile.llvm_generation_ms = elapsed_ms(llvm_start);

  if (llvm::verifyModule(*result.module, &llvm::errs()))
    fail("E260", "LLVM backend generated an invalid module.", {});
  auto optimization_start = Clock::now();
  optimize(*result.module);
  result.profile.optimization_ms = elapsed_ms(optimization_start);
  if (llvm::verifyModule(*result.module, &llvm::errs()))
    fail("E260", "Optimized LLVM module failed verification.", {});

  result.manifest =
      VariantManifest{variant_id,
                      seed,
                      frontend.source_hash,
                      jir_hash,
                      "",
                      LLVM_VERSION_STRING,
                      result.module->getTargetTriple(),
                      options.execution_mode,
                      options.profile,
                      std::nullopt,
                      std::nullopt,
                      structural_metrics(*result.module, std::move(strategies), helpers.size()),
                      std::move(pool),
                      utc_now()};
  result.manifest.llvm_ir_hash = sha256(render_llvm_ir(result));
  return result;
}

std::string render_llvm_ir(const LoweredVariant &variant) {
  std::string output;
  llvm::raw_string_ostream stream(output);
  variant.module->print(stream, nullptr);
  stream.flush();
  return output;
}

void emit_aot_object(LoweredVariant &variant, const std::string &path) {
  auto start = Clock::now();
  std::string error;
  auto machine = target_machine(error, variant.manifest.target_triple);
  if (machine == nullptr || machine->getTargetTriple().str() != variant.manifest.target_triple)
    fail("E263", "Requested host TargetMachine is unavailable: " + error, {});
  std::error_code file_error;
  llvm::raw_fd_ostream output(path, file_error, llvm::sys::fs::OF_None);
  if (file_error)
    fail("E264", "Cannot create AOT output: " + file_error.message(), {});
  llvm::legacy::PassManager passes;
  if (machine->addPassesToEmitFile(passes, output, nullptr, llvm::CodeGenFileType::ObjectFile))
    fail("E263", "LLVM target cannot emit an object file.", {});
  auto object_module = llvm::CloneModule(*variant.module);
  passes.run(*object_module);
  output.flush();
  variant.profile.aot_ms = elapsed_ms(start);
  variant.manifest.artifact_hash = file_sha256(path);
}

jocky_status execute_orc(LoweredVariant &&variant, jocky_context *runtime, StageProfile &profile,
                         std::string &error) {
  auto compile_start = Clock::now();
  if (llvm::InitializeNativeTarget() || llvm::InitializeNativeTargetAsmPrinter()) {
    error = "Native LLVM target initialization failed";
    return JOCKY_INTERNAL_ERROR;
  }
  auto jit = llvm::orc::LLJITBuilder().create();
  if (!jit) {
    error = llvm::toString(jit.takeError());
    return JOCKY_INTERNAL_ERROR;
  }
  auto generator = llvm::orc::DynamicLibrarySearchGenerator::GetForCurrentProcess(
      (*jit)->getDataLayout().getGlobalPrefix());
  if (!generator) {
    error = llvm::toString(generator.takeError());
    return JOCKY_INTERNAL_ERROR;
  }
  (*jit)->getMainJITDylib().addGenerator(std::move(*generator));
  variant.module->setDataLayout((*jit)->getDataLayout());
  variant.module->setTargetTriple((*jit)->getTargetTriple().str());
  auto symbol_name = variant.entry_symbol;
  if (auto failure = (*jit)->addIRModule(
          llvm::orc::ThreadSafeModule(std::move(variant.module), std::move(variant.context)))) {
    error = llvm::toString(std::move(failure));
    return JOCKY_INTERNAL_ERROR;
  }
  auto symbol = (*jit)->lookup(symbol_name);
  if (!symbol) {
    error = llvm::toString(symbol.takeError());
    return JOCKY_INTERNAL_ERROR;
  }
  profile.jit_compile_ms = elapsed_ms(compile_start);
  auto execution_start = Clock::now();
  auto entry = symbol->toPtr<uint32_t (*)(jocky_context *)>();
  auto status = static_cast<jocky_status>(entry(runtime));
  profile.execution_ms = elapsed_ms(execution_start);
  return status;
}

llvm::json::Object profile_json(const StageProfile &profile) {
  auto measured = [](const std::optional<double> &value) -> llvm::json::Value {
    return value ? llvm::json::Value(*value) : llvm::json::Value(nullptr);
  };
  return llvm::json::Object{{"schema_version", "1.0.0"},
                            {"clock", "steady_clock"},
                            {"units", "milliseconds"},
                            {"lex_ms", measured(profile.lex_ms)},
                            {"parse_ms", measured(profile.parse_ms)},
                            {"semantic_ms", measured(profile.semantic_ms)},
                            {"jir_ms", measured(profile.jir_ms)},
                            {"variant_ms", measured(profile.variant_ms)},
                            {"llvm_generation_ms", measured(profile.llvm_generation_ms)},
                            {"optimization_ms", measured(profile.optimization_ms)},
                            {"aot_ms", measured(profile.aot_ms)},
                            {"jit_compile_ms", measured(profile.jit_compile_ms)},
                            {"execution_ms", measured(profile.execution_ms)}};
}

llvm::json::Object manifest_json(const VariantManifest &manifest) {
  llvm::json::Array strategies;
  for (auto strategy : manifest.structural.lowering_strategy_ids)
    strategies.push_back(static_cast<int64_t>(strategy));
  llvm::json::Value encryption = nullptr;
  if (manifest.literal_pool) {
    const auto &pool = *manifest.literal_pool;
    encryption = llvm::json::Object{{"enabled", true},
                                    {"algorithm", pool.algorithm},
                                    {"key_id", pool.key_id},
                                    {"encrypted_pool_digest", pool.digest},
                                    {"nonce", bytes_hex(pool.nonce.data(), pool.nonce.size())},
                                    {"nonce_policy", pool.nonce_policy},
                                    {"associated_data_hash", sha256(pool.associated_data)}};
  } else {
    encryption = llvm::json::Object{{"enabled", false}};
  }
  return llvm::json::Object{
      {"schema_version", "1.0.0"},
      {"kind", "VariantManifest"},
      {"variant_id", manifest.variant_id},
      {"variant_seed", manifest.variant_seed},
      {"source_hash", manifest.source_hash},
      {"jir_hash", manifest.jir_hash},
      {"llvm_ir_hash", manifest.llvm_ir_hash},
      {"compiler_version", compiler_version},
      {"llvm_version", manifest.llvm_version},
      {"target_triple", manifest.target_triple},
      {"execution_mode", manifest.execution_mode},
      {"profile", manifest.profile},
      {"artifact_hash", manifest.artifact_hash ? llvm::json::Value(*manifest.artifact_hash)
                                               : llvm::json::Value(nullptr)},
      {"semantic_result_hash", manifest.semantic_result_hash
                                   ? llvm::json::Value(*manifest.semantic_result_hash)
                                   : llvm::json::Value(nullptr)},
      {"structural_fingerprint", manifest.structural.fingerprint},
      {"structural_metrics",
       llvm::json::Object{
           {"llvm_basic_block_count", static_cast<int64_t>(manifest.structural.basic_block_count)},
           {"function_count", static_cast<int64_t>(manifest.structural.function_count)},
           {"generated_helper_count",
            static_cast<int64_t>(manifest.structural.generated_helper_count)},
           {"selected_lowering_strategy_ids", std::move(strategies)}}},
      {"literal_pool", std::move(encryption)},
      {"created_at", manifest.created_at}};
}

std::string manifest_summary(const VariantManifest &manifest) {
  std::ostringstream output;
  output << "variant_id: " << manifest.variant_id << '\n'
         << "seed: " << manifest.variant_seed << '\n'
         << "target: " << manifest.target_triple << '\n'
         << "execution: " << manifest.execution_mode << '\n'
         << "llvm_ir_hash: " << manifest.llvm_ir_hash << '\n'
         << "artifact_hash: " << manifest.artifact_hash.value_or("unavailable") << '\n'
         << "semantic_result_hash: " << manifest.semantic_result_hash.value_or("unavailable")
         << '\n'
         << "structural_fingerprint: " << manifest.structural.fingerprint << '\n';
  return output.str();
}

void write_manifest(const VariantManifest &manifest, const std::string &path) {
  std::ofstream output(path, std::ios::binary);
  if (!output)
    fail("E264", "Cannot create variant manifest.", {});
  output << canonical_json(manifest_json(manifest)) << '\n';
  if (!output)
    fail("E264", "Failed to write variant manifest.", {});
}

VariantManifest read_manifest(const std::string &path) {
  std::ifstream input(path, std::ios::binary);
  if (!input)
    fail("E265", "Cannot open variant manifest.", {});
  std::ostringstream bytes;
  bytes << input.rdbuf();
  auto parsed = llvm::json::parse(bytes.str());
  if (!parsed || parsed->getAsObject() == nullptr)
    fail("E265", "Variant manifest is not valid JSON.", {});
  const auto &object = *parsed->getAsObject();
  auto required = [&](llvm::StringRef key) {
    auto value = object.getString(key);
    if (!value)
      fail("E265", "Variant manifest is missing `" + key.str() + "`.", {});
    return value->str();
  };
  StructuralMetrics structural;
  structural.fingerprint = required("structural_fingerprint");
  if (auto *metrics = object.getObject("structural_metrics")) {
    structural.basic_block_count = metrics->getInteger("llvm_basic_block_count").value_or(0);
    structural.function_count = metrics->getInteger("function_count").value_or(0);
    structural.generated_helper_count = metrics->getInteger("generated_helper_count").value_or(0);
    if (auto *strategies = metrics->getArray("selected_lowering_strategy_ids"))
      for (const auto &value : *strategies)
        if (auto integer = value.getAsInteger())
          structural.lowering_strategy_ids.push_back(static_cast<uint32_t>(*integer));
  }
  return VariantManifest{required("variant_id"),
                         required("variant_seed"),
                         required("source_hash"),
                         required("jir_hash"),
                         required("llvm_ir_hash"),
                         required("llvm_version"),
                         required("target_triple"),
                         required("execution_mode"),
                         required("profile"),
                         optional_string(object, "artifact_hash"),
                         optional_string(object, "semantic_result_hash"),
                         std::move(structural),
                         std::nullopt,
                         required("created_at")};
}
} // namespace jocky
