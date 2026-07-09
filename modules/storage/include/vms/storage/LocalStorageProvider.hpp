#pragma once

#include <filesystem>
#include <string>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief Local filesystem storage provider.
class LocalStorageProvider final : public IStorageProvider {
public:
    explicit LocalStorageProvider(std::filesystem::path rootPath);

    [[nodiscard]] Result<StorageVolume> describe() const override;
    [[nodiscard]] Result<void> verify(const std::string& path) const override;
    [[nodiscard]] Result<std::string> allocateSegmentPath(
        const CameraId& cameraId,
        Timestamp startTime) override;

private:
    std::filesystem::path rootPath_;
    Uuid volumeId_;
};

}  // namespace vms
