#pragma once
#include "jocky/jir.h"

namespace jocky {
Type project_type(const Type &input, const std::vector<std::string> &fields, Span span);
int64_t limit_value(const ExprPtr &expression, Span span);
void pushdown_candidate(FrontendModule &module, int64_t input, int64_t branch,
                        const std::string &kind, llvm::json::Object attributes);
} // namespace jocky
