#pragma once

#include "vms/common/ServiceRegistry.hpp"

namespace vms {

/// @brief Bootstraps and wires core server services.
class ServerHost {
public:
    ServerHost();
    void start();
    void stop();

    [[nodiscard]] ServiceRegistry& registry() { return registry_; }

private:
    ServiceRegistry registry_;
    bool running_{false};
};

}  // namespace vms
