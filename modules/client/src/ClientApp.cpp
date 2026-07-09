#include "vms/client/ClientApp.hpp"

#include "vms/api/RestApi.hpp"
#include "vms/api/WebSocketApi.hpp"
#include "vms/common/Logging.hpp"

#include <iostream>

namespace vms::client {

int ClientApp::run(int argc, char** argv) const {
    const auto serverUrl = parseServerUrl(argc, argv);
    if (serverUrl.empty()) {
        printUsage();
        return 1;
    }

    printBanner();
    vms::logger().log(vms::LogLevel::Info, "vms_client", "Target server: " + serverUrl);
    printCapabilities();

    return 0;
}

void ClientApp::printBanner() {
    std::cout << "Enterprise VMS Windows Client (Phase 1 bootstrap)\n";
    std::cout << "--------------------------------------------------\n";
}

void ClientApp::printUsage() {
    std::cout << "Usage: vms_client --server <url>\n";
    std::cout << "Example: vms_client --server http://127.0.0.1:8080\n";
}

void ClientApp::printCapabilities() {
    std::cout << "Available REST routes:\n";
    for (const auto& route : vms::api::restRoutes()) {
        std::cout << "  " << route.method << " " << route.path << " - " << route.summary << '\n';
    }

    std::cout << "\nWebSocket channels:\n";
    for (const auto& channel : vms::api::webSocketChannels()) {
        std::cout << "  " << channel << '\n';
    }
}

std::string ClientApp::parseServerUrl(int argc, char** argv) {
    for (int i = 1; i + 1 < argc; ++i) {
        if (std::string(argv[i]) == "--server") {
            return argv[i + 1];
        }
    }
    return {};
}

}  // namespace vms::client
