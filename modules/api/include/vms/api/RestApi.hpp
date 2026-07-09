#pragma once

/// @file RestApi.hpp
/// @brief REST API contract definitions (Phase 2: HTTP server binding).

#include <string>
#include <vector>

#include "vms/core/Types.hpp"

namespace vms::api {

/// @brief Describes a REST route exposed by the VMS gateway.
struct RestRoute {
    std::string method;
    std::string path;
    std::string summary;
};

/// @brief Returns the versioned REST surface for OpenAPI generation.
[[nodiscard]] inline std::vector<RestRoute> restRoutes() {
    return {
        {"GET", "/api/v1/health", "Server health and uptime"},
        {"POST", "/api/v1/auth/login", "Authenticate user and issue token"},
        {"GET", "/api/v1/cameras", "List configured cameras"},
        {"POST", "/api/v1/cameras", "Create or update a camera"},
        {"GET", "/api/v1/cameras/{id}/streams", "Get stream metadata"},
        {"POST", "/api/v1/cameras/{id}/record/start", "Start recording"},
        {"POST", "/api/v1/cameras/{id}/record/stop", "Stop recording"},
        {"GET", "/api/v1/playback/segments", "Query recorded segments"},
        {"GET", "/api/v1/events", "List recent events"},
        {"GET", "/api/v1/storage/volumes", "List storage volumes"}};
}

}  // namespace vms::api
