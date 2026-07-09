#pragma once

#include <mutex>
#include <vector>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief Coordinates camera configuration, health, and stream metadata.
class CameraManager final : public ICameraManager {
public:
    explicit CameraManager(std::shared_ptr<ICameraRepository> repository);

    void onStatusChanged(CameraStatusCallback callback) override;
    [[nodiscard]] Result<StreamInfo> getStreamInfo(
        const CameraId& id,
        StreamProfile profile) const override;
    Result<void> setEnabled(const CameraId& id, bool enabled) override;
    Result<void> reconnect(const CameraId& id) override;

private:
    std::shared_ptr<ICameraRepository> repository_;
    mutable std::mutex mutex_;
    std::vector<CameraStatusCallback> statusCallbacks_;
};

}  // namespace vms
