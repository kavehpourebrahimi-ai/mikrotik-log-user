#include "vms/auth/AuthorizationService.hpp"

#include <algorithm>
#include <unordered_set>

namespace vms {

void AuthorizationService::addRole(const Role& role) {
    std::lock_guard lock(mutex_);
    roles_[role.roleId] = role;
}

bool AuthorizationService::hasPermission(
    const User& user,
    Permission permission) const {
    const auto permissions = listPermissions(user);
    return std::find(permissions.begin(), permissions.end(), permission)
        != permissions.end();
}

std::vector<Permission> AuthorizationService::listPermissions(
    const User& user) const {
    std::lock_guard lock(mutex_);
    std::unordered_set<Permission> unique;

    for (const auto& roleId : user.roleIds) {
        const auto it = roles_.find(roleId);
        if (it == roles_.end()) {
            continue;
        }
        for (const auto permission : it->second.permissions) {
            unique.insert(permission);
        }
    }

    return {unique.begin(), unique.end()};
}

}  // namespace vms
