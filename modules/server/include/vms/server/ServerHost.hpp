#pragma once

#include "vms/common/ServiceRegistry.hpp"

#include <memory>

namespace vms {

class HttpApiServer;

/// @brief Bootstraps and wires core server services.
class ServerHost {
public:
    ServerHost();
    ~ServerHost();
    void start();
    void stop();

    [[nodiscard]] ServiceRegistry& registry() { return registry_; }

private:
    ServiceRegistry registry_;
    bool running_{false};
    int apiPort_{8080};
    std::unique_ptr<HttpApiServer> apiServer_;
};

}  // namespace vms
