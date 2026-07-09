#pragma once

#include <mutex>
#include <unordered_map>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief Coordinates storage providers and retention policies.
class StorageManager final : public IStorageManager {
public:
    Result<void> registerProvider(
        const Uuid& providerId,
        std::shared_ptr<IStorageProvider> provider) override;

    [[nodiscard]] std::vector<StorageVolume> listVolumes() const override;
    Result<std::uint64_t> enforceRetention(Duration maxAge) override;

private:
    mutable std::mutex mutex_;
    std::unordered_map<std::string, std::shared_ptr<IStorageProvider>> providers_;
};

}  // namespace vms
