#include "jocky/parser.h"
#include <algorithm>

namespace jocky {
const Token &Parser::peek() const { return tokens_.at(cursor_); }
Token Parser::take() {
  auto token = peek();
  if (token.kind != TokenKind::End)
    ++cursor_;
  return token;
}
bool Parser::match(const std::string &text) {
  if (peek().kind != TokenKind::End && peek().text == text) {
    take();
    return true;
  }
  return false;
}
Token Parser::expect(const std::string &text) {
  if (peek().text != text || peek().kind == TokenKind::End)
    fail("E120", "Expected `" + text + "`.", peek().span);
  return take();
}
Token Parser::atom() {
  if (peek().kind != TokenKind::Word && peek().kind != TokenKind::Keyword &&
      peek().kind != TokenKind::String && peek().kind != TokenKind::Number)
    fail("E120", "Expected a name or literal.", peek().span);
  return take();
}
std::string Parser::name(bool binding) {
  if (peek().kind != TokenKind::Word && (binding || peek().kind != TokenKind::Keyword))
    fail("E120", binding ? "Expected a non-reserved binding name." : "Expected a name.",
         peek().span);
  auto result = take().text;
  while (!binding && match("."))
    result += "." + atom().text;
  return result;
}
std::vector<std::string> Parser::fields() {
  expect("[");
  std::vector<std::string> result;
  if (!match("]")) {
    do {
      result.push_back(name());
    } while (match(",") && peek().text != "]");
    expect("]");
  }
  return result;
}
ExprPtr Parser::value() {
  auto token = atom();
  std::string kind = token.kind == TokenKind::String ? "string" : "word";
  if (token.kind == TokenKind::Number)
    kind = "number";
  if (token.text == "true" || token.text == "false")
    kind = "bool";
  auto text = token.value;
  if (kind == "number" && (peek().text == "%" || peek().text == "B" || peek().text == "KB" ||
                           peek().text == "MB" || peek().text == "GB" || peek().text == "KiB" ||
                           peek().text == "MiB" || peek().text == "GiB" || peek().text == "ms" ||
                           peek().text == "s" || peek().text == "m" || peek().text == "h")) {
    auto unit = take();
    text += unit.text;
    token.span.end = unit.span.end;
    kind = "quantity";
  }
  return std::make_shared<Expr>(Expr{Expr::Kind::Literal, text, kind, token.span, {}});
}
static int precedence(const std::string &op) {
  if (op == "or")
    return 1;
  if (op == "and")
    return 2;
  if (op == "==" || op == "!=")
    return 3;
  if (op == "<" || op == "<=" || op == ">" || op == ">=")
    return 4;
  if (op == "+" || op == "-")
    return 5;
  if (op == "*" || op == "/")
    return 6;
  return 0;
}
ExprPtr Parser::expression(int minimum) {
  if (++depth_ > 64)
    fail("E122", "Expression nesting exceeds 64 levels.", peek().span);
  ExprPtr left;
  auto start = peek().span.start;
  if (match("(")) {
    left = expression();
    expect(")");
  } else if (peek().text == "not" || peek().text == "-") {
    auto op = take();
    auto operand = expression(7);
    if (op.text == "-" && operand->kind == Expr::Kind::Literal &&
        operand->literal_kind == "number" && !operand->value.starts_with('-')) {
      operand->value = "-" + operand->value;
      operand->span.start = start;
      left = operand;
    } else
      left = std::make_shared<Expr>(Expr{Expr::Kind::Unary,
                                         op.text,
                                         "",
                                         {start, operand->span.end},
                                         {operand},
                                         operand->height + 1});
  } else if (peek().kind == TokenKind::String || peek().kind == TokenKind::Number ||
             peek().text == "true" || peek().text == "false")
    left = value();
  else {
    auto identifier = name();
    left = std::make_shared<Expr>(
        Expr{Expr::Kind::Name, identifier, "", {start, tokens_[cursor_ - 1].span.end}, {}});
    if (match("(")) {
      left->kind = Expr::Kind::Call;
      if (!match(")")) {
        do {
          left->children.push_back(expression());
        } while (match(","));
        expect(")");
      }
      left->span.end = tokens_[cursor_ - 1].span.end;
      for (const auto &child : left->children)
        left->height = std::max(left->height, child->height + 1);
    }
  }
  while (precedence(peek().text) > minimum) {
    auto op = take();
    auto right = expression(precedence(op.text));
    auto height = 1 + std::max(left->height, right->height);
    if (height > 64)
      fail("E122", "Expression tree exceeds 64 levels.", {start, right->span.end});
    left = std::make_shared<Expr>(
        Expr{Expr::Kind::Binary, op.text, "", {start, right->span.end}, {left, right}, height});
  }
  if (left->height > 64)
    fail("E122", "Expression tree exceeds 64 levels.", left->span);
  --depth_;
  return left;
}
void Parser::settings(std::map<std::string, Option> &output, const std::string &context,
                      Program *program) {
  expect("{");
  while (!match("}")) {
    auto key = atom();
    if (output.contains(key.text))
      fail("E123", "Duplicate " + context + " option `" + key.text + "`.", key.span);
    if (key.text == "variant" && program != nullptr) {
      if (!program->variant.empty())
        fail("E123", "Duplicate variant block.", key.span);
      settings(program->variant, "variant");
      output.emplace("variant", Option{"variant", nullptr, {}, key.span});
      continue;
    }
    if (context == "budget")
      expect("<=");
    auto v = value();
    output.emplace(key.text, Option{key.text, v, {}, {key.span.start, v->span.end}});
    match(";");
  }
}
void Parser::selectors(Program &program, bool block) {
  if (block)
    expect("{");
  if (block && match("}"))
    return;
  do {
    auto key = atom();
    if (key.text == "os") {
      do {
        auto os = atom();
        program.target_os.push_back(os.value);
        program.selectors.push_back({"os", os.value, os.span});
      } while (match("|"));
    } else if (key.text == "group" || key.text == "host" || key.text == "target") {
      if (peek().kind != TokenKind::String)
        fail("E120", "Selector value must be a quoted string.", peek().span);
      auto v = take();
      program.selectors.push_back({key.text, v.value, {key.span.start, v.span.end}});
    } else
      fail("E124", "Unknown target selector `" + key.text + "`.", key.span);
    match(";");
  } while (block && peek().text != "}");
  if (block)
    expect("}");
}
Statement Parser::statement() {
  auto token = take();
  Statement s{};
  s.span.start = token.span.start;
  if (token.text == "collect") {
    s.kind = Statement::Kind::Collect;
    s.collector = name();
    if (s.collector == "scheduled" && match("tasks"))
      s.collector = "scheduled_tasks";
    if (match("{")) {
      while (!match("}")) {
        auto key = atom();
        Option option{key.text, nullptr, {}, key.span};
        if (key.text == "fields")
          option.fields = fields();
        else
          option.value = expression();
        option.span.end = tokens_[cursor_ - 1].span.end;
        s.options.push_back(std::move(option));
        match(";");
      }
    }
    expect("as");
    s.name = name(true);
  } else if (token.text == "let") {
    s.kind = Statement::Kind::Let;
    s.name = name(true);
    expect("=");
    s.expression = expression();
    while (match("|")) {
      auto op = atom();
      PipelineOp p{};
      p.kind = op.text;
      p.span.start = op.span.start;
      if (op.text == "where" || op.text == "limit")
        p.expression = expression();
      else if (op.text == "select")
        p.fields = fields();
      else if (op.text == "sort") {
        p.fields.push_back(name());
        if (peek().text == "asc" || peek().text == "desc")
          p.direction = take().text;
      } else if (op.text == "group") {
        expect("by");
        p.fields = fields();
      } else
        fail("E125", "Unknown pipeline operator `" + op.text + "`.", op.span);
      p.span.end = tokens_[cursor_ - 1].span.end;
      s.pipeline.push_back(std::move(p));
    }
  } else if (token.text == "correlate") {
    s.kind = Statement::Kind::Correlate;
    s.expression = expression();
    expect("with");
    s.right = expression();
    expect("as");
    s.name = name(true);
  } else if (token.text == "finding") {
    s.kind = Statement::Kind::Finding;
    if (peek().kind != TokenKind::String)
      fail("E120", "Finding title must be quoted.", peek().span);
    s.name = take().value;
    expect("{");
    std::set<std::string> seen;
    while (!match("}")) {
      auto key = atom();
      if (!seen.insert(key.text).second)
        fail("E123", "Duplicate finding clause.", key.span);
      if (key.text == "when")
        s.expression = expression();
      else if (key.text == "severity")
        s.severity = atom().value;
      else if (key.text == "evidence")
        s.sources.push_back(name());
      else
        fail("E126", "Unknown finding clause `" + key.text + "`.", key.span);
      match(";");
    }
    if (!s.expression || s.severity.empty() || s.sources.empty())
      fail("E126", "Finding requires when, severity and evidence.",
           {token.span.start, tokens_[cursor_ - 1].span.end});
  } else if (token.text == "timeline") {
    s.kind = Statement::Kind::Timeline;
    expect("{");
    while (!match("}")) {
      expect("source");
      s.sources.push_back(name());
      match(";");
    }
  } else if (token.text == "export" || token.text == "report") {
    s.kind = Statement::Kind::Report;
    if (token.text == "export")
      expect("report");
    expect("{");
    std::set<std::string> seen;
    while (!match("}")) {
      auto key = atom();
      if (key.text != "include" && !seen.insert(key.text).second)
        fail("E123", "Duplicate report clause.", key.span);
      if (key.text == "format")
        s.format = atom().value;
      else if (key.text == "include")
        s.sources.push_back(atom().value);
      else if (key.text == "integrity") {
        auto v = atom();
        if (v.text != "true" && v.text != "false")
          fail("E127", "integrity expects true or false.", v.span);
        s.integrity = v.text == "true";
      } else
        fail("E127", "Unknown report clause.", key.span);
      match(";");
    }
  } else if (token.text == "analyze") {
    s.kind = Statement::Kind::Analyze;
    s.sources.push_back(name());
    if (match("as"))
      s.name = name(true);
    if (match("{"))
      statements(s.children);
  } else
    fail("E121", "Unexpected statement `" + token.text + "`.", token.span);
  s.span.end = tokens_[cursor_ - 1].span.end;
  match(";");
  return s;
}
void Parser::statements(std::vector<Statement> &output) {
  if (++depth_ > 64)
    fail("E122", "Statement nesting exceeds 64 levels.", peek().span);
  while (!match("}")) {
    if (peek().kind == TokenKind::End)
      fail("E120", "Expected `}` before end of source.", peek().span);
    output.push_back(statement());
  }
  --depth_;
}
Program Parser::parse() {
  Program p;
  p.span.start = peek().span.start;
  bool case_block = false;
  if (match("case")) {
    if (peek().kind != TokenKind::String)
      fail("E120", "Case label must be quoted.", peek().span);
    p.case_name = take().value;
    case_block = match("{");
  }
  expect("hunt");
  if (peek().kind != TokenKind::String)
    fail("E120", "Hunt label must be quoted.", peek().span);
  p.hunt_name = take().value;
  expect("{");
  std::set<std::string> seen;
  bool has_statements = false;
  while (!match("}")) {
    auto key = peek();
    bool declaration = key.text == "targets" || key.text == "target" || key.text == "runtime" ||
                       key.text == "capabilities" || key.text == "budget" || key.text == "group" ||
                       key.text == "host" || key.text == "os";
    if (!declaration) {
      has_statements = true;
      p.statements.push_back(statement());
      continue;
    }
    if (has_statements)
      fail("E128", "Declarations must precede statements.", key.span);
    if (key.text == "group" || key.text == "host" || key.text == "os" ||
        (key.text == "target" && tokens_.at(cursor_ + 1).text != "{")) {
      selectors(p, false);
      continue;
    }
    take();
    auto block_key = key.text == "target" ? "targets" : key.text;
    if (!seen.insert(block_key).second)
      fail("E123", "Duplicate declaration block.", key.span);
    if (block_key == "targets")
      selectors(p, true);
    else if (key.text == "runtime")
      settings(p.runtime, "runtime", &p);
    else if (key.text == "budget")
      settings(p.budgets, "budget");
    else {
      expect("{");
      while (!match("}")) {
        p.capabilities.push_back(name());
        match(";");
      }
    }
  }
  if (case_block)
    expect("}");
  p.span.end = tokens_[cursor_ - 1].span.end;
  if (peek().kind != TokenKind::End)
    fail("E129", "One hunt is allowed per compilation unit.", peek().span);
  return p;
}
} // namespace jocky
