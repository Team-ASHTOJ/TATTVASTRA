#include "jocky/literal_pool.h"

#include <limits>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/rand.h>

namespace jocky {
namespace {
void append_u32(std::vector<uint8_t> &output, uint32_t value) {
  for (unsigned shift = 0; shift < 32; shift += 8)
    output.push_back(static_cast<uint8_t>(value >> shift));
}

unsigned nibble(char value) {
  if (value >= '0' && value <= '9')
    return static_cast<unsigned>(value - '0');
  if (value >= 'a' && value <= 'f')
    return static_cast<unsigned>(value - 'a' + 10);
  if (value >= 'A' && value <= 'F')
    return static_cast<unsigned>(value - 'A' + 10);
  fail("E262", "Literal key must contain exactly 64 hexadecimal digits.", {});
}
} // namespace

std::vector<uint8_t> parse_aes256_key_hex(const std::string &text) {
  if (text.size() != 64)
    fail("E262", "Literal key must contain exactly 64 hexadecimal digits.", {});
  std::vector<uint8_t> key(32);
  for (size_t index = 0; index < key.size(); ++index)
    key[index] =
        static_cast<uint8_t>((nibble(text[index * 2]) << 4U) | nibble(text[index * 2 + 1]));
  return key;
}

ProtectedLiteralPool protect_literal_pool(const FrontendModule &module,
                                          const std::vector<uint8_t> &key,
                                          const std::string &key_id,
                                          const std::string &associated_data) {
  if (key.size() != 32 || key_id.empty())
    fail("E262", "Literal protection requires a 256-bit key and nonempty key ID.", {});
  std::vector<uint8_t> plaintext;
  append_u32(plaintext, static_cast<uint32_t>(module.instructions.size()));
  for (const auto &instruction : module.instructions) {
    auto attributes = canonical_json(llvm::json::Value(llvm::json::Object(instruction.attributes)));
    if (attributes.size() > std::numeric_limits<uint32_t>::max())
      fail("E262", "Literal pool item is too large.", instruction.span);
    append_u32(plaintext, static_cast<uint32_t>(instruction.id));
    append_u32(plaintext, static_cast<uint32_t>(attributes.size()));
    plaintext.insert(plaintext.end(), attributes.begin(), attributes.end());
  }

  ProtectedLiteralPool result;
  result.key_id = key_id;
  result.associated_data = associated_data;
  if (RAND_bytes(result.nonce.data(), static_cast<int>(result.nonce.size())) != 1)
    fail("E262", "Cryptographic nonce generation failed.", {});
  result.ciphertext.resize(plaintext.size());
  auto *cipher = EVP_CIPHER_CTX_new();
  int written = 0, total = 0;
  bool ok = cipher != nullptr &&
            EVP_EncryptInit_ex(cipher, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) == 1 &&
            EVP_CIPHER_CTX_ctrl(cipher, EVP_CTRL_GCM_SET_IVLEN,
                                static_cast<int>(result.nonce.size()), nullptr) == 1 &&
            EVP_EncryptInit_ex(cipher, nullptr, nullptr, key.data(), result.nonce.data()) == 1;
  if (ok && !associated_data.empty())
    ok = EVP_EncryptUpdate(cipher, nullptr, &written,
                           reinterpret_cast<const uint8_t *>(associated_data.data()),
                           static_cast<int>(associated_data.size())) == 1;
  if (ok)
    ok = EVP_EncryptUpdate(cipher, result.ciphertext.data(), &written, plaintext.data(),
                           static_cast<int>(plaintext.size())) == 1;
  total = written;
  if (ok)
    ok = EVP_EncryptFinal_ex(cipher, result.ciphertext.data() + total, &written) == 1;
  total += written;
  if (ok)
    ok = EVP_CIPHER_CTX_ctrl(cipher, EVP_CTRL_GCM_GET_TAG, static_cast<int>(result.tag.size()),
                             result.tag.data()) == 1;
  EVP_CIPHER_CTX_free(cipher);
  OPENSSL_cleanse(plaintext.data(), plaintext.size());
  if (!ok)
    fail("E262", "AES-256-GCM literal encryption failed.", {});
  result.ciphertext.resize(static_cast<size_t>(total));
  std::string authenticated_bytes(reinterpret_cast<const char *>(result.nonce.data()),
                                  result.nonce.size());
  authenticated_bytes.append(reinterpret_cast<const char *>(result.tag.data()), result.tag.size());
  authenticated_bytes.append(reinterpret_cast<const char *>(result.ciphertext.data()),
                             result.ciphertext.size());
  authenticated_bytes += result.associated_data;
  result.digest = sha256(authenticated_bytes);
  return result;
}
} // namespace jocky
