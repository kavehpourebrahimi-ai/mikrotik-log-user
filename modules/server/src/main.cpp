#include "vms/server/ServerHost.hpp"

#include "vms/common/Logging.hpp"

#include <atomic>
#include <chrono>
#include <csignal>
#include <string>
#include <thread>

namespace {
std::atomic<bool> g_running{true};
std::atomic<bool> g_serviceMode{false};

void handleSignal(int) {
    g_running = false;
}
}  // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--service") {
            g_serviceMode = true;
        }
    }

    std::signal(SIGINT, handleSignal);
    std::signal(SIGTERM, handleSignal);

    vms::ServerHost host;
    host.start();

    vms::logger().log(
        vms::LogLevel::Info,
        "vms_server",
        "REST API: GET /api/v1/health, POST /api/v1/auth/login");
    if (g_serviceMode) {
        vms::logger().log(vms::LogLevel::Info, "vms_server", "Running in service-compatible mode");
    }
    vms::logger().log(vms::LogLevel::Info, "vms_server", "Press Ctrl+C to stop");

    while (g_running) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    host.stop();
    return 0;
}
