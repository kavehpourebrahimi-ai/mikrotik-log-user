#pragma once

#include <string>

namespace vms {

/// @brief Generates a RFC-4122-style UUID string.
[[nodiscard]] std::string generateUuid();

}  // namespace vms
