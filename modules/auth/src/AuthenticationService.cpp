#include "vms/auth/AuthenticationService.hpp"

#include "vms/common/Uuid.hpp"

#include <functional>
#include <sstream>

namespace vms {
namespace {

std::string makeToken() {
    return "vms-" + generateUuid();
}

}  // namespace

AuthenticationService::AuthenticationService() {
    User admin;
    admin.userId = generateUuid();
    admin.username = "admin";
    admin.displayName = "System Administrator";
    admin.enabled = true;

    Role adminRole;
    adminRole.roleId = generateUuid();
    adminRole.name = "Administrator";
    adminRole.permissions = {
        Permission::ViewLive,
        Permission::ViewPlayback,
        Permission::ExportFootage,
        Permission::ManageCameras,
        Permission::ManageUsers,
        Permission::ManageStorage,
        Permission::ManageAlarms,
        Permission::ManagePlugins,
        Permission::PtzControl,
        Permission::SystemAdmin};

    admin.roleIds.push_back(adminRole.roleId);
    createUser(admin, "admin");
}

std::string AuthenticationService::hashPassword(std::string_view password) {
    return std::to_string(std::hash<std::string>{}(std::string(password)));
}

Result<std::string> AuthenticationService::authenticate(
    std::string_view username,
    std::string_view password) const {
    std::lock_guard lock(mutex_);
    const auto it = users_.find(std::string(username));
    if (it == users_.end()) {
        return Result<std::string>::failure("Invalid credentials");
    }

    if (!it->second.user.enabled) {
        return Result<std::string>::failure("User is disabled");
    }

    if (it->second.passwordHash != hashPassword(password)) {
        return Result<std::string>::failure("Invalid credentials");
    }

    const auto token = makeToken();
    tokenToUser_[token] = it->second.user.userId;
    return Result<std::string>::success(token);
}

Result<User> AuthenticationService::validateToken(std::string_view token) const {
    std::lock_guard lock(mutex_);
    const auto tokenIt = tokenToUser_.find(std::string(token));
    if (tokenIt == tokenToUser_.end()) {
        return Result<User>::failure("Invalid token");
    }

    for (const auto& [_, record] : users_) {
        if (record.user.userId == tokenIt->second) {
            return Result<User>::success(record.user);
        }
    }

    return Result<User>::failure("User not found for token");
}

Result<void> AuthenticationService::createUser(
    const User& user,
    std::string_view password) {
    if (user.username.empty()) {
        return Result<void>::failure("Username is required");
    }

    std::lock_guard lock(mutex_);
    users_[user.username] = CredentialRecord{user, hashPassword(password)};
    return Result<void>::success();
}

}  // namespace vms
