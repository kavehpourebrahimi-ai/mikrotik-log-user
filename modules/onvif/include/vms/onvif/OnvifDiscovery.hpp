#pragma once

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief ONVIF WS-Discovery placeholder (Phase 2: SOAP/WS-Discovery stack).
class OnvifDiscovery final : public IOnvifDiscovery {
public:
    [[nodiscard]] Result<std::vector<CameraDescriptor>> discover(
        Duration timeout) override;

    [[nodiscard]] Result<CameraDescriptor> configure(
        const CameraDescriptor& discovered,
        std::string_view username,
        std::string_view password) override;
};

}  // namespace vms
