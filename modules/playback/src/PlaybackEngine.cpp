#include "vms/playback/PlaybackEngine.hpp"

namespace vms {

Result<std::vector<RecordingSegment>> PlaybackEngine::querySegments(
    const CameraId& cameraId,
    Timestamp from,
    Timestamp to) const {
    std::lock_guard lock(mutex_);
    std::vector<RecordingSegment> segments;

    for (const auto& segment : index_) {
        if (segment.cameraId.value != cameraId.value) {
            continue;
        }
        if (segment.endTime >= from && segment.startTime <= to) {
            segments.push_back(segment);
        }
    }

    return Result<std::vector<RecordingSegment>>::success(std::move(segments));
}

Result<void> PlaybackEngine::seek(const CameraId& cameraId, Timestamp position) {
    (void)cameraId;
    (void)position;
    return Result<void>::success();
}

void PlaybackEngine::onPlaybackFrame(MediaFrameCallback callback) {
    std::lock_guard lock(mutex_);
    playbackCallback_ = std::move(callback);
}

}  // namespace vms
