#pragma once

#include <mutex>
#include <unordered_map>

#include "vms/core/Interfaces.hpp"

namespace vms {

class StreamSession final : public IStreamSession {
public:
    explicit StreamSession(StreamInfo stream);

    Result<void> start(const StreamInfo& stream) override;
    void stop() override;
    [[nodiscard]] bool isActive() const override;
    void onFrame(MediaFrameCallback callback) override;

private:
    StreamInfo stream_;
    bool active_{false};
    MediaFrameCallback frameCallback_;
};

/// @brief Reference-counted RTSP ingest pipeline (Phase 2: native RTSP stack).
class StreamPipeline final : public IStreamPipeline {
public:
    [[nodiscard]] std::shared_ptr<IStreamSession> acquire(
        const CameraId& cameraId,
        StreamProfile profile) override;

    void release(
        const CameraId& cameraId,
        StreamProfile profile) override;

private:
    struct SessionKey {
        std::string cameraId;
        StreamProfile profile;

        [[nodiscard]] bool operator==(const SessionKey& other) const noexcept {
            return cameraId == other.cameraId && profile == other.profile;
        }
    };

    struct SessionKeyHash {
        std::size_t operator()(const SessionKey& key) const noexcept {
            return std::hash<std::string>{}(key.cameraId)
                ^ (static_cast<std::size_t>(key.profile) << 1);
        }
    };

    std::mutex mutex_;
    std::unordered_map<SessionKey, std::weak_ptr<StreamSession>, SessionKeyHash> sessions_;
};

}  // namespace vms
