#pragma once
#include "jocky/ast.h"
#include <set>

namespace jocky {
class Parser {
  const std::vector<Token> &tokens_;
  std::size_t cursor_ = 0;
  std::size_t depth_ = 0;
  const Token &peek() const;
  Token take();
  bool match(const std::string &text);
  Token expect(const std::string &text);
  Token atom();
  std::string name(bool binding = false);
  std::vector<std::string> fields();
  ExprPtr value();
  ExprPtr expression(int precedence = 0);
  Statement statement();
  void statements(std::vector<Statement> &output);
  void selectors(Program &program, bool block);
  void settings(std::map<std::string, Option> &output, const std::string &context,
                Program *program = nullptr);

public:
  explicit Parser(const std::vector<Token> &tokens) : tokens_(tokens) {}
  Program parse();
};
} // namespace jocky
