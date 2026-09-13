#include "jocky/source.h"
#include <cctype>
#include <llvm/Support/Error.h>
#include <set>

namespace jocky {
std::vector<Token> lex(const std::string &source) {
  if (source.size() > 262144)
    fail("E100", "Source exceeds 256 KiB.", {});
  if (!llvm::json::isUTF8(source))
    fail("E101", "Source is not valid UTF-8.", {});
  std::vector<Token> tokens;
  Position current;
  auto peek = [&](std::size_t delta = 0) -> char {
    return current.offset + delta < source.size() ? source[current.offset + delta] : '\0';
  };
  auto advance = [&]() {
    char c = source[current.offset++];
    if (c == '\n') {
      ++current.line;
      current.column = 1;
    } else {
      ++current.column;
    }
  };
  auto digit = [](char c) { return c >= '0' && c <= '9'; };
  auto alpha = [](char c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_'; };
  auto emit = [&](TokenKind kind, Position start, std::string value = "") {
    auto text = source.substr(start.offset, current.offset - start.offset);
    tokens.push_back({kind, text, kind == TokenKind::String ? value : text, {start, current}});
    if (tokens.size() > 32768)
      fail("E100", "Source exceeds 32768 tokens.", {start, current});
  };
  while (current.offset < source.size()) {
    if (std::isspace(static_cast<unsigned char>(peek()))) {
      advance();
      continue;
    }
    auto start = current;
    if (peek() == '/' && peek(1) == '/') {
      while (current.offset < source.size() && peek() != '\n')
        advance();
      continue;
    }
    if (peek() == '/' && peek(1) == '*') {
      advance();
      advance();
      while (current.offset < source.size() && !(peek() == '*' && peek(1) == '/'))
        advance();
      if (current.offset == source.size())
        fail("E102", "Unterminated block comment.", {start, current});
      advance();
      advance();
      continue;
    }
    if (peek() == '"') {
      advance();
      bool closed = false;
      while (current.offset < source.size()) {
        if (peek() == '\n' || peek() == '\r')
          break;
        if (peek() == '"') {
          advance();
          closed = true;
          break;
        }
        if (peek() == '\\') {
          advance();
          if (current.offset >= source.size())
            break;
        }
        advance();
      }
      if (!closed)
        fail("E103", "Unterminated string literal.", {start, current});
      auto decoded = llvm::json::parse(source.substr(start.offset, current.offset - start.offset));
      if (!decoded) {
        llvm::consumeError(decoded.takeError());
        fail("E104", "Invalid JSON string escape or control character.", {start, current});
      }
      emit(TokenKind::String, start, decoded->getAsString()->str());
      continue;
    }
    if (alpha(peek())) {
      while (alpha(peek()) || digit(peek()))
        advance();
      auto word = source.substr(start.offset, current.offset - start.offset);
      emit(is_keyword(word) ? TokenKind::Keyword : TokenKind::Word, start);
      continue;
    }
    if (digit(peek())) {
      if (peek() == '0' && peek(1) == 'x') {
        advance();
        advance();
        while (std::isxdigit(static_cast<unsigned char>(peek())))
          advance();
      } else {
        while (digit(peek()))
          advance();
        if (peek() == '.' && digit(peek(1))) {
          advance();
          while (digit(peek()))
            advance();
        }
        if (peek() == 'e' || peek() == 'E') {
          advance();
          if (peek() == '+' || peek() == '-')
            advance();
          if (!digit(peek()))
            fail("E105", "Invalid numeric exponent.", {start, current});
          while (digit(peek()))
            advance();
        }
      }
      emit(TokenKind::Number, start);
      continue;
    }
    static const std::set<std::string> pairs = {"<=", ">=", "==", "!="};
    auto pair = source.substr(current.offset, 2);
    if (pairs.contains(pair)) {
      advance();
      advance();
      emit(TokenKind::Symbol, start);
      continue;
    }
    if (std::string("{}[](),.|=<>+-*/%;").find(peek()) != std::string::npos && peek() != '\0') {
      advance();
      emit(TokenKind::Symbol, start);
      continue;
    }
    advance();
    fail("E106", "Unexpected character in source.", {start, current});
  }
  tokens.push_back({TokenKind::End, "", "", {current, current}});
  return tokens;
}
} // namespace jocky
