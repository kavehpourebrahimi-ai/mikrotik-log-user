#include <catch2/catch_test_macros.hpp>

#include "vms/auth/AuthenticationService.hpp"
#include "vms/auth/AuthorizationService.hpp"

TEST_CASE("AuthenticationService issues and validates tokens", "[auth]") {
    vms::AuthenticationService auth;
    const auto token = auth.authenticate("admin", "admin");
    REQUIRE(token.ok());

    const auto user = auth.validateToken(*token.value);
    REQUIRE(user.ok());
    REQUIRE(user.value->username == "admin");
}

TEST_CASE("AuthorizationService evaluates role permissions", "[auth]") {
    vms::AuthorizationService authz;

    vms::Role operatorRole;
    operatorRole.roleId = "role-operator";
    operatorRole.name = "Operator";
    operatorRole.permissions = {
        vms::Permission::ViewLive,
        vms::Permission::ViewPlayback};
    authz.addRole(operatorRole);

    vms::User user;
    user.userId = "user-1";
    user.username = "operator";
    user.roleIds.push_back(operatorRole.roleId);

    REQUIRE(authz.hasPermission(user, vms::Permission::ViewLive));
    REQUIRE_FALSE(authz.hasPermission(user, vms::Permission::ManageUsers));
}
