#pragma once

#include <mutex>
#include <unordered_map>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief Role-based authorization service.
class AuthorizationService final : public IAuthorizationService {
public:
    void addRole(const Role& role);

    [[nodiscard]] bool hasPermission(
        const User& user,
        Permission permission) const override;

    [[nodiscard]] std::vector<Permission> listPermissions(
        const User& user) const override;

private:
    mutable std::mutex mutex_;
    std::unordered_map<std::string, Role> roles_;
};

}  // namespace vms
