#pragma once

#include <string>
#include <string_view>
#include <unordered_map>

namespace vms {

/// @brief Simple key-value configuration loaded from files or memory.
class Config {
public:
    /// @brief Loads configuration from `key=value` lines.
    [[nodiscard]] static Config fromFile(const std::string& path);

    /// @brief Returns a configuration value or default if missing.
    [[nodiscard]] std::string get(
        std::string_view key,
        std::string_view defaultValue = {}) const;

    /// @brief Sets a configuration value.
    void set(std::string_view key, std::string_view value);

    /// @brief Returns whether a key exists.
    [[nodiscard]] bool contains(std::string_view key) const;

private:
    std::unordered_map<std::string, std::string> values_;
};

}  // namespace vms
