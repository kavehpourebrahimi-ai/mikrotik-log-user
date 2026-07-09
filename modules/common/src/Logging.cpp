#include "vms/common/Logging.hpp"

#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>

namespace vms {
namespace {

std::mutex g_loggerMutex;
std::shared_ptr<ILogger> g_logger = std::make_shared<ConsoleLogger>();

const char* levelToString(LogLevel level) {
    switch (level) {
        case LogLevel::Trace:
            return "TRACE";
        case LogLevel::Debug:
            return "DEBUG";
        case LogLevel::Info:
            return "INFO";
        case LogLevel::Warn:
            return "WARN";
        case LogLevel::Error:
            return "ERROR";
    }
    return "INFO";
}

}  // namespace

void ConsoleLogger::log(
    LogLevel level,
    std::string_view component,
    std::string_view message) {
    const auto now = std::chrono::system_clock::now();
    const auto time = std::chrono::system_clock::to_time_t(now);

    std::ostringstream stream;
    stream << std::put_time(std::localtime(&time), "%F %T")
           << " [" << levelToString(level) << "] "
           << component << " - " << message;

    std::cout << stream.str() << std::endl;
}

ILogger& logger() {
    std::lock_guard lock(g_loggerMutex);
    return *g_logger;
}

void setLogger(std::shared_ptr<ILogger> loggerInstance) {
    std::lock_guard lock(g_loggerMutex);
    g_logger = std::move(loggerInstance);
}

}  // namespace vms
