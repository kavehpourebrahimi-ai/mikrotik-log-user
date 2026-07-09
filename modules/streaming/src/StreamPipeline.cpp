#include "vms/streaming/StreamPipeline.hpp"

namespace vms {

StreamSession::StreamSession(StreamInfo stream) : stream_(std::move(stream)) {}

Result<void> StreamSession::start(const StreamInfo& stream) {
    if (stream.uri.empty()) {
        return Result<void>::failure("Stream URI is required");
    }

    stream_ = stream;
    active_ = true;
    return Result<void>::success();
}

void StreamSession::stop() {
    active_ = false;
}

bool StreamSession::isActive() const {
    return active_;
}

void StreamSession::onFrame(MediaFrameCallback callback) {
    frameCallback_ = std::move(callback);
}

std::shared_ptr<IStreamSession> StreamPipeline::acquire(
    const CameraId& cameraId,
    StreamProfile profile) {
    const SessionKey key{cameraId.value, profile};
    std::lock_guard lock(mutex_);

    if (const auto it = sessions_.find(key); it != sessions_.end()) {
        if (auto existing = it->second.lock()) {
            return existing;
        }
    }

    StreamInfo info;
    info.cameraId = cameraId;
    info.profile = profile;

    auto session = std::make_shared<StreamSession>(info);
    sessions_[key] = session;
    return session;
}

void StreamPipeline::release(
    const CameraId& cameraId,
    StreamProfile profile) {
    const SessionKey key{cameraId.value, profile};
    std::lock_guard lock(mutex_);
    sessions_.erase(key);
}

}  // namespace vms
