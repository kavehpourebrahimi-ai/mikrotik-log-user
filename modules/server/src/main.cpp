#include "vms/server/ServerHost.hpp"

#include "vms/common/Logging.hpp"

#include <atomic>
#include <chrono>
#include <csignal>
#include <thread>

namespace {
std::atomic<bool> g_running{true};

void handleSignal(int) {
    g_running = false;
}
}  // namespace

int main() {
    std::signal(SIGINT, handleSignal);
    std::signal(SIGTERM, handleSignal);

    vms::ServerHost host;
    host.start();

    vms::logger().log(
        vms::LogLevel::Info,
        "vms_server",
        "Press Ctrl+C to stop");

    while (g_running) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    host.stop();
    return 0;
}
