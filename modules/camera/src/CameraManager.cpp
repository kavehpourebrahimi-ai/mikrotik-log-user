#include "vms/camera/CameraManager.hpp"

#include "vms/common/Logging.hpp"

namespace vms {

CameraManager::CameraManager(std::shared_ptr<ICameraRepository> repository)
    : repository_(std::move(repository)) {}

void CameraManager::onStatusChanged(CameraStatusCallback callback) {
    std::lock_guard lock(mutex_);
    statusCallbacks_.push_back(std::move(callback));
}

Result<StreamInfo> CameraManager::getStreamInfo(
    const CameraId& id,
    StreamProfile profile) const {
    const auto cameraResult = repository_->get(id);
    if (!cameraResult.ok()) {
        return Result<StreamInfo>::failure(cameraResult.error);
    }

    const auto& camera = *cameraResult.value;
    StreamInfo info;
    info.cameraId = camera.id;
    info.profile = profile;
    info.codec = VideoCodec::H264;
    info.transport = TransportProtocol::Tcp;

    if (profile == StreamProfile::Main) {
        info.uri = camera.mainStreamUri;
    } else {
        info.uri = camera.subStreamUri.empty() ? camera.mainStreamUri : camera.subStreamUri;
    }

    return Result<StreamInfo>::success(info);
}

Result<void> CameraManager::setEnabled(const CameraId& id, bool enabled) {
    auto cameraResult = repository_->get(id);
    if (!cameraResult.ok()) {
        return Result<void>::failure(cameraResult.error);
    }

    auto camera = *cameraResult.value;
    camera.enabled = enabled;
    camera.status = enabled ? CameraStatus::Online : CameraStatus::Disabled;

    const auto upsertResult = repository_->upsert(camera);
    if (!upsertResult.ok()) {
        return upsertResult;
    }

    std::vector<CameraStatusCallback> callbacks;
    {
        std::lock_guard lock(mutex_);
        callbacks = statusCallbacks_;
    }

    for (const auto& callback : callbacks) {
        callback(id, camera.status);
    }

    logger().log(
        LogLevel::Info,
        "CameraManager",
        enabled ? "Camera enabled" : "Camera disabled");

    return Result<void>::success();
}

Result<void> CameraManager::reconnect(const CameraId& id) {
    const auto cameraResult = repository_->get(id);
    if (!cameraResult.ok()) {
        return Result<void>::failure(cameraResult.error);
    }

    auto camera = *cameraResult.value;
    if (!camera.enabled) {
        return Result<void>::failure("Camera is disabled");
    }

    camera.status = CameraStatus::Online;
    return repository_->upsert(camera);
}

}  // namespace vms
