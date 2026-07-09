#pragma once

#include <mutex>
#include <unordered_map>
#include <vector>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief Thread-safe in-memory camera repository for development and tests.
class InMemoryCameraRepository final : public ICameraRepository {
public:
    [[nodiscard]] std::vector<CameraDescriptor> list() const override;
    [[nodiscard]] Result<CameraDescriptor> get(const CameraId& id) const override;
    Result<void> upsert(const CameraDescriptor& camera) override;
    Result<void> remove(const CameraId& id) override;

private:
    mutable std::mutex mutex_;
    std::unordered_map<std::string, CameraDescriptor> cameras_;
};

}  // namespace vms
