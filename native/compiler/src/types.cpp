#include "jocky/types.h"
#include <charconv>
#include <cmath>
#include <limits>
#include <regex>

namespace jocky {
Type scalar(TypeKind kind, bool nullable) { return {kind, nullable, "", {}}; }
std::string type_name(const Type &t) {
  static const char *names[] = {"invalid", "int", "float", "bool", "string", "time",    "duration",
                                "hash",    "ip",  "path",  "pid",  "bytes",  "Dataset", "Record"};
  std::string name = names[static_cast<int>(t.kind)];
  if (t.kind == TypeKind::Dataset || t.kind == TypeKind::Record)
    name += "<" + t.domain + ">";
  return t.nullable ? "Option<" + name + ">" : name;
}
llvm::json::Object type_json(const Type &t) {
  llvm::json::Object fields;
  for (const auto &[name, type] : t.fields)
    fields[name] = type_json(type);
  return llvm::json::Object{{"name", type_name(t)},
                            {"nullable", t.nullable},
                            {"domain", t.domain},
                            {"fields", std::move(fields)}};
}
Type field_type(const Type &row, const std::string &path, Span span) {
  if (auto exact = row.fields.find(path); exact != row.fields.end())
    return exact->second;
  auto split = path.find('.');
  auto head = path.substr(0, split);
  auto found = row.fields.find(head);
  if (found == row.fields.end())
    fail("E213", "Type `" + type_name(row) + "` has no field `" + head + "`.", span,
         "Use a field in the input's projected schema.");
  auto result = found->second;
  if (split != std::string::npos) {
    auto tail = path.substr(split + 1);
    if (result.kind == TypeKind::IP && tail == "is_public")
      return scalar(TypeKind::Bool, result.nullable);
    if (result.kind != TypeKind::Record)
      fail("E214", "Cannot access a field on `" + type_name(result) + "`.", span);
    result = field_type(result, tail, span);
  }
  return result;
}
bool numeric(const Type &t) { return t.kind == TypeKind::Int || t.kind == TypeKind::Float; }
bool comparable(const Type &a, const Type &b, bool ordering) {
  if (a.kind == TypeKind::Dataset || a.kind == TypeKind::Record || b.kind == TypeKind::Dataset ||
      b.kind == TypeKind::Record)
    return false;
  if (a.kind != b.kind && !(numeric(a) && numeric(b)))
    return false;
  return !ordering || a.kind != TypeKind::Bool;
}
int64_t quantity(const std::string &text, const std::string &unit_class, Span span) {
  static const std::map<std::string, int64_t> units = {
      {"%", 1},           {"B", 1},      {"KB", 1000},     {"MB", 1000000},
      {"GB", 1000000000}, {"KiB", 1024}, {"MiB", 1048576}, {"GiB", 1073741824},
      {"ms", 1},          {"s", 1000},   {"m", 60000},     {"h", 3600000}};
  auto split = text.find_first_not_of("0123456789");
  if (split == 0 || split == std::string::npos)
    fail("E232", "Expected an integer with an explicit " + unit_class + " unit.", span);
  auto suffix = text.substr(split);
  auto found = units.find(suffix);
  bool duration = suffix == "ms" || suffix == "s" || suffix == "m" || suffix == "h";
  if (found == units.end() || (unit_class == "duration" && !duration) ||
      (unit_class == "bytes" && (duration || suffix == "%")) ||
      (unit_class == "cpu" && suffix != "%"))
    fail("E232", "Invalid " + unit_class + " unit.", span);
  int64_t value = 0;
  auto converted = std::from_chars(text.data(), text.data() + split, value);
  if (converted.ec != std::errc() || value > 9007199254740991LL / found->second)
    fail("E232", "Quantity exceeds the portable integer range.", span);
  return value * found->second;
}
Type literal_type(const Expr &e) {
  if (e.literal_kind == "string")
    return scalar(TypeKind::String);
  if (e.literal_kind == "bool")
    return scalar(TypeKind::Bool);
  if (e.literal_kind == "quantity") {
    bool duration = e.value.ends_with("ms") || e.value.ends_with("s") || e.value.ends_with("m") ||
                    e.value.ends_with("h");
    quantity(e.value, duration ? "duration" : "bytes", e.span);
    return scalar(duration ? TypeKind::Duration : TypeKind::Bytes);
  }
  if (e.literal_kind == "number") {
    if (e.value.find_first_of(".eE") != std::string::npos && !e.value.starts_with("0x")) {
      double value = 0;
      auto parsed = std::from_chars(e.value.data(), e.value.data() + e.value.size(), value);
      if (parsed.ec != std::errc() || parsed.ptr != e.value.data() + e.value.size() ||
          !std::isfinite(value))
        fail("E220", "Float literal must be finite and representable.", e.span);
      return scalar(TypeKind::Float);
    }
    int64_t value = 0;
    auto parsed = std::from_chars(e.value.data(), e.value.data() + e.value.size(), value);
    if (parsed.ec != std::errc() || parsed.ptr != e.value.data() + e.value.size())
      fail("E220", "Integer literal is outside signed 64-bit decimal range.", e.span);
    return scalar(TypeKind::Int);
  }
  fail("E220", "Expected a typed literal.", e.span);
}
static bool ipv4(const std::string &text) {
  std::size_t start = 0;
  for (int i = 0; i < 4; ++i) {
    auto end = text.find('.', start);
    if (end == std::string::npos)
      end = text.size();
    auto part = text.substr(start, end - start);
    unsigned value = 0;
    auto result = std::from_chars(part.data(), part.data() + part.size(), value);
    if (part.empty() || part.size() > 3 || (part.size() > 1 && part[0] == '0') ||
        result.ec != std::errc() || result.ptr != part.data() + part.size() || value > 255)
      return false;
    if (i == 3)
      return end == text.size();
    if (end == text.size())
      return false;
    start = end + 1;
  }
  return false;
}
static bool ip_address(const std::string &text) {
  if (text.find(":::") != std::string::npos)
    return false;
  if (text.find(':') == std::string::npos)
    return ipv4(text);
  auto compressed = text.find("::");
  if (compressed != std::string::npos && text.find("::", compressed + 2) != std::string::npos)
    return false;
  if ((text.starts_with(':') && !text.starts_with("::")) ||
      (text.ends_with(':') && !text.ends_with("::")))
    return false;
  unsigned groups = 0;
  std::size_t start = 0;
  while (start < text.size()) {
    auto end = text.find(':', start);
    if (end == std::string::npos)
      end = text.size();
    auto part = text.substr(start, end - start);
    if (!part.empty()) {
      if (part.find('.') != std::string::npos) {
        if (end != text.size() || !ipv4(part))
          return false;
        groups += 2;
      } else {
        if (part.size() > 4 ||
            part.find_first_not_of("0123456789abcdefABCDEF") != std::string::npos)
          return false;
        ++groups;
      }
    } else if (end != 0 && text[end - 1] == ':' && end + 1 < text.size() && text[end + 1] == ':')
      return false;
    start = end + 1;
  }
  return compressed == std::string::npos ? groups == 8 : groups < 8;
}
void validate_constructor(const std::string &name, const Expr &argument, Span span) {
  if (argument.kind != Expr::Kind::Literal)
    fail("E226", "Typed constructors require a literal argument.", span);
  const auto &value = argument.value;
  if (name == "pid" || name == "bytes") {
    if (literal_type(argument).kind != TypeKind::Int || value.starts_with('-'))
      fail("E226", name + " requires a nonnegative integer literal.", span);
    uint64_t number = 0;
    std::from_chars(value.data(), value.data() + value.size(), number);
    if (name == "pid" && number > 4294967295ULL)
      fail("E226", "PID exceeds 32 bits.", span);
    return;
  }
  if (name == "duration") {
    quantity(value, "duration", span);
    return;
  }
  if (argument.literal_kind != "string")
    fail("E226", name + " requires a string literal.", span);
  if (name == "path" && (value.empty() || value.find('\0') != std::string::npos))
    fail("E226", "Path must be nonempty and contain no NUL.", span);
  if (name == "ip" && !ip_address(value))
    fail("E226", "Malformed IPv4/IPv6 literal.", span);
  if (name == "hash" &&
      (value.size() != 64 || value.find_first_not_of("0123456789abcdef") != std::string::npos))
    fail("E226", "Hash must be 64 lowercase SHA-256 hexadecimal digits.", span);
  if (name == "time") {
    static const std::regex pattern(
        R"((\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d{1,9})?Z)");
    std::smatch parts;
    if (!std::regex_match(value, parts, pattern))
      fail("E226", "Time requires an ISO-8601 UTC timestamp ending in Z.", span);
    int year = std::stoi(parts[1]), month = std::stoi(parts[2]), day = std::stoi(parts[3]);
    bool leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    int days[] = {31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (year == 0 || month < 1 || month > 12 || day < 1 || day > days[month - 1] ||
        std::stoi(parts[4]) > 23 || std::stoi(parts[5]) > 59 || std::stoi(parts[6]) > 59)
      fail("E226", "Time contains an invalid calendar date or clock value.", span);
  }
}
} // namespace jocky
