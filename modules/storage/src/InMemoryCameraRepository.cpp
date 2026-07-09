#include "vms/storage/InMemoryCameraRepository.hpp"

namespace vms {

std::vector<CameraDescriptor> InMemoryCameraRepository::list() const {
    std::lock_guard lock(mutex_);
    std::vector<CameraDescriptor> cameras;
    cameras.reserve(cameras_.size());
    for (const auto& [_, camera] : cameras_) {
        cameras.push_back(camera);
    }
    return cameras;
}

Result<CameraDescriptor> InMemoryCameraRepository::get(const CameraId& id) const {
    std::lock_guard lock(mutex_);
    const auto it = cameras_.find(id.value);
    if (it == cameras_.end()) {
        return Result<CameraDescriptor>::failure("Camera not found: " + id.value);
    }
    return Result<CameraDescriptor>::success(it->second);
}

Result<void> InMemoryCameraRepository::upsert(const CameraDescriptor& camera) {
    if (camera.id.value.empty()) {
        return Result<void>::failure("Camera id is required");
    }

    std::lock_guard lock(mutex_);
    cameras_[camera.id.value] = camera;
    return Result<void>::success();
}

Result<void> InMemoryCameraRepository::remove(const CameraId& id) {
    std::lock_guard lock(mutex_);
    if (!cameras_.erase(id.value)) {
        return Result<void>::failure("Camera not found: " + id.value);
    }
    return Result<void>::success();
}

}  // namespace vms
