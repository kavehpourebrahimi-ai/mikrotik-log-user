#pragma once

#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief JSON-file backed persistent camera repository.
class FileCameraRepository final : public ICameraRepository {
public:
    explicit FileCameraRepository(std::string filePath);

    [[nodiscard]] std::vector<CameraDescriptor> list() const override;
    [[nodiscard]] Result<CameraDescriptor> get(const CameraId& id) const override;
    Result<void> upsert(const CameraDescriptor& camera) override;
    Result<void> remove(const CameraId& id) override;

private:
    Result<void> loadFromDisk();
    Result<void> persistToDisk() const;

    std::string filePath_;
    mutable std::mutex mutex_;
    std::unordered_map<std::string, CameraDescriptor> cameras_;
};

}  // namespace vms
