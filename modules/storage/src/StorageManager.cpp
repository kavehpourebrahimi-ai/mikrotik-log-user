#include "vms/storage/StorageManager.hpp"

namespace vms {

Result<void> StorageManager::registerProvider(
    const Uuid& providerId,
    std::shared_ptr<IStorageProvider> provider) {
    if (!provider) {
        return Result<void>::failure("Provider cannot be null");
    }

    std::lock_guard lock(mutex_);
    providers_[providerId] = std::move(provider);
    return Result<void>::success();
}

std::vector<StorageVolume> StorageManager::listVolumes() const {
    std::lock_guard lock(mutex_);
    std::vector<StorageVolume> volumes;
    volumes.reserve(providers_.size());

    for (const auto& [_, provider] : providers_) {
        const auto result = provider->describe();
        if (result.ok()) {
            volumes.push_back(*result.value);
        }
    }

    return volumes;
}

Result<std::uint64_t> StorageManager::enforceRetention(Duration maxAge) {
    if (maxAge.count() <= 0) {
        return Result<std::uint64_t>::failure("Retention duration must be positive");
    }

    // Phase 1: retention scanning is delegated to the recording index in a later phase.
    return Result<std::uint64_t>::success(0);
}

}  // namespace vms
