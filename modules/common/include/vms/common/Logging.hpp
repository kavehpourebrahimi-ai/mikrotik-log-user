#pragma once

#include <memory>
#include <mutex>
#include <string>
#include <string_view>

namespace vms {

enum class LogLevel : std::uint8_t {
    Trace = 0,
    Debug = 1,
    Info = 2,
    Warn = 3,
    Error = 4
};

/// @brief Structured logging sink interface.
class ILogger {
public:
    virtual ~ILogger() = default;

    virtual void log(
        LogLevel level,
        std::string_view component,
        std::string_view message) = 0;
};

/// @brief Thread-safe console logger for server diagnostics.
class ConsoleLogger final : public ILogger {
public:
    void log(
        LogLevel level,
        std::string_view component,
        std::string_view message) override;
};

/// @brief Returns the process-wide logger instance.
ILogger& logger();

/// @brief Replaces the process-wide logger instance.
void setLogger(std::shared_ptr<ILogger> logger);

}  // namespace vms
