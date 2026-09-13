#pragma once
#include <cstddef>
#include <llvm/Support/JSON.h>
#include <stdexcept>
#include <string>
#include <vector>

namespace jocky {
struct Position {
  std::size_t offset = 0;
  std::size_t line = 1;
  std::size_t column = 1;
};
struct Span {
  Position start;
  Position end;
};
struct Diagnostic {
  std::string code;
  std::string message;
  Span span;
  std::string help;
  std::string severity = "error";
};
class FrontendError : public std::runtime_error {
public:
  Diagnostic diagnostic;
  explicit FrontendError(Diagnostic value)
      : std::runtime_error(value.message), diagnostic(std::move(value)) {}
};
[[noreturn]] void fail(std::string code, std::string message, Span span, std::string help = "");
llvm::json::Object span_json(const Span &span);
llvm::json::Object diagnostic_json(const Diagnostic &diagnostic, const std::string &source);
std::string render_diagnostic(const Diagnostic &diagnostic, const std::string &source,
                              const std::string &filename);
std::string canonical_json(const llvm::json::Value &value);
std::string sha256(const std::string &bytes);
bool is_keyword(const std::string &text);

enum class TokenKind { Word, Keyword, Number, String, Symbol, End };
struct Token {
  TokenKind kind;
  std::string text;
  std::string value;
  Span span;
};
std::string token_kind_name(TokenKind kind);
std::vector<Token> lex(const std::string &source);
llvm::json::Array tokens_json(const std::vector<Token> &tokens);
} // namespace jocky
