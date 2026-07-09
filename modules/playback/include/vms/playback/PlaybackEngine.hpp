#pragma once

#include <mutex>
#include <vector>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief Playback engine with segment index queries (Phase 3: demux/decode).
class PlaybackEngine final : public IPlaybackEngine {
public:
    [[nodiscard]] Result<std::vector<RecordingSegment>> querySegments(
        const CameraId& cameraId,
        Timestamp from,
        Timestamp to) const override;

    Result<void> seek(const CameraId& cameraId, Timestamp position) override;
    void onPlaybackFrame(MediaFrameCallback callback) override;

private:
    mutable std::mutex mutex_;
    MediaFrameCallback playbackCallback_;
    std::vector<RecordingSegment> index_;
};

}  // namespace vms
