#include "jocky/source.h"
#include <algorithm>
#include <iomanip>
#include <llvm/Support/FormatVariadic.h>
#include <llvm/Support/SHA256.h>
#include <set>
#include <sstream>

namespace jocky {
[[noreturn]] void fail(std::string code, std::string message, Span span, std::string help) {
  throw FrontendError({std::move(code), std::move(message), span, std::move(help)});
}
llvm::json::Object span_json(const Span &span) {
  auto position = [](const Position &p) {
    return llvm::json::Object{{"offset", static_cast<int64_t>(p.offset)},
                              {"line", static_cast<int64_t>(p.line)},
                              {"column", static_cast<int64_t>(p.column)}};
  };
  return llvm::json::Object{{"start", position(span.start)}, {"end", position(span.end)}};
}
static std::string source_line(const std::string &source, const Span &span) {
  auto start =
      span.start.offset == 0 ? std::string::npos : source.rfind('\n', span.start.offset - 1);
  start = start == std::string::npos ? 0 : start + 1;
  auto end = source.find('\n', start);
  return source.substr(start, end == std::string::npos ? end : end - start);
}
llvm::json::Object diagnostic_json(const Diagnostic &d, const std::string &source) {
  return llvm::json::Object{{"code", d.code},         {"message", d.message},
                            {"severity", d.severity}, {"span", span_json(d.span)},
                            {"help", d.help},         {"source_line", source_line(source, d.span)}};
}
std::string render_diagnostic(const Diagnostic &d, const std::string &source,
                              const std::string &filename) {
  std::ostringstream out;
  out << filename << ':' << d.span.start.line << ':' << d.span.start.column << ": JOCKY " << d.code
      << ": " << d.message << '\n';
  auto line = source_line(source, d.span);
  out << line << '\n';
  // Preserve tabs so carets line up with the terminal's tab stops.
  for (std::size_t i = 0; i + 1 < d.span.start.column; ++i)
    out << (i < line.size() && line[i] == '\t' ? '\t' : ' ');
  auto width = d.span.end.line == d.span.start.line ? d.span.end.column - d.span.start.column : 1;
  out << std::string(std::clamp<std::size_t>(width, 1, 100), '^') << '\n';
  if (!d.help.empty())
    out << "help: " << d.help << '\n';
  return out.str();
}
std::string canonical_json(const llvm::json::Value &value) {
  if (const auto *object = value.getAsObject()) {
    std::vector<std::string> keys;
    for (const auto &item : *object)
      keys.push_back(item.first.str());
    std::sort(keys.begin(), keys.end());
    std::string output = "{";
    for (const auto &key : keys) {
      if (output.size() > 1)
        output += ',';
      output += llvm::formatv("{0}", llvm::json::Value(key)).str() + ":" +
                canonical_json(*object->get(key));
    }
    return output + "}";
  }
  if (const auto *array = value.getAsArray()) {
    std::string output = "[";
    for (const auto &item : *array) {
      if (output.size() > 1)
        output += ',';
      output += canonical_json(item);
    }
    return output + "]";
  }
  return llvm::formatv("{0}", value).str();
}
std::string sha256(const std::string &bytes) {
  llvm::SHA256 hash;
  hash.update(bytes);
  std::ostringstream out;
  for (auto byte : hash.final())
    out << std::hex << std::setw(2) << std::setfill('0') << unsigned(byte);
  return out.str();
}
bool is_keyword(const std::string &text) {
  static const std::set<std::string> words = {
      "case",         "hunt",    "target",    "targets", "group",    "host",      "os",
      "runtime",      "backend", "execution", "variant", "enabled",  "seed",      "profile",
      "capabilities", "budget",  "cpu",       "memory",  "io",       "duration",  "collect",
      "as",           "let",     "where",     "select",  "sort",     "limit",     "count",
      "correlate",    "with",    "finding",   "when",    "severity", "evidence",  "timeline",
      "source",       "report",  "export",    "include", "format",   "integrity", "analyze",
      "fields",       "true",    "false",     "and",     "or",       "not",       "asc",
      "desc",         "by",      "join",      "on"};
  return words.contains(text);
}
std::string token_kind_name(TokenKind kind) {
  switch (kind) {
  case TokenKind::Word:
    return "identifier";
  case TokenKind::Keyword:
    return "keyword";
  case TokenKind::Number:
    return "number";
  case TokenKind::String:
    return "string";
  case TokenKind::Symbol:
    return "symbol";
  case TokenKind::End:
    return "eof";
  }
  return "invalid";
}
llvm::json::Array tokens_json(const std::vector<Token> &tokens) {
  llvm::json::Array result;
  for (const auto &t : tokens)
    result.push_back(llvm::json::Object{{"kind", token_kind_name(t.kind)},
                                        {"text", t.text},
                                        {"value", t.value},
                                        {"span", span_json(t.span)}});
  return result;
}
} // namespace jocky
