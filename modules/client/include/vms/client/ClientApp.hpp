#pragma once

#include <string>
#include <vector>

namespace vms::client {

/// @brief Minimal client shell for server discovery and API introspection.
class ClientApp {
public:
    int run(int argc, char** argv) const;

private:
    static void printBanner();
    static void printUsage();
    static void printCapabilities();
    static std::string parseServerUrl(int argc, char** argv);
};

}  // namespace vms::client
