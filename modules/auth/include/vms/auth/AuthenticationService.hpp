#pragma once

#include <mutex>
#include <unordered_map>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief In-memory authentication service with hashed credential storage.
class AuthenticationService final : public IAuthenticationService {
public:
    AuthenticationService();

    [[nodiscard]] Result<std::string> authenticate(
        std::string_view username,
        std::string_view password) const override;

    [[nodiscard]] Result<User> validateToken(std::string_view token) const override;

    Result<void> createUser(
        const User& user,
        std::string_view password);

private:
    struct CredentialRecord {
        User user;
        std::string passwordHash;
    };

    [[nodiscard]] static std::string hashPassword(std::string_view password);

    mutable std::mutex mutex_;
    std::unordered_map<std::string, CredentialRecord> users_;
    mutable std::unordered_map<std::string, std::string> tokenToUser_;
};

}  // namespace vms
