#pragma once

#include "jocky/jir.h"
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace jocky {
struct ProtectedLiteralPool {
  std::string algorithm = "AES-256-GCM";
  std::string key_id;
  std::string nonce_policy = "RANDOM_96_BIT_UNIQUE_PER_KEY";
  std::array<uint8_t, 12> nonce{};
  std::array<uint8_t, 16> tag{};
  std::vector<uint8_t> ciphertext;
  std::string associated_data;
  std::string digest;
};

std::vector<uint8_t> parse_aes256_key_hex(const std::string &text);
ProtectedLiteralPool protect_literal_pool(const FrontendModule &module,
                                          const std::vector<uint8_t> &key,
                                          const std::string &key_id,
                                          const std::string &associated_data);
} // namespace jocky
