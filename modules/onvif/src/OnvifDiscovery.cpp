#include "vms/onvif/OnvifDiscovery.hpp"

namespace vms {

Result<std::vector<CameraDescriptor>> OnvifDiscovery::discover(Duration timeout) {
    (void)timeout;
    return Result<std::vector<CameraDescriptor>>::success({});
}

Result<CameraDescriptor> OnvifDiscovery::configure(
    const CameraDescriptor& discovered,
    std::string_view username,
    std::string_view password) {
    auto configured = discovered;
    configured.username = std::string(username);
    configured.password = std::string(password);
    return Result<CameraDescriptor>::success(configured);
}

}  // namespace vms
