#include "vms/recording/RecordingEngine.hpp"

#include "vms/common/Logging.hpp"

namespace vms {

RecordingEngine::RecordingEngine(
    std::shared_ptr<IStorageManager> storageManager,
    std::shared_ptr<IStreamPipeline> streamPipeline)
    : storageManager_(std::move(storageManager)),
      streamPipeline_(std::move(streamPipeline)) {}

Result<void> RecordingEngine::startRecording(
    const CameraId& cameraId,
    RecordingMode mode) {
    auto session = streamPipeline_->acquire(cameraId, StreamProfile::Main);
    const StreamInfo stream{
        cameraId,
        StreamProfile::Main,
        VideoCodec::H264,
        TransportProtocol::Tcp,
        {},
        0,
        0,
        0};

    const auto startResult = session->start(stream);
    if (!startResult.ok()) {
        return startResult;
    }

    std::lock_guard lock(mutex_);
    activeRecordings_.insert(cameraId.value);

    logger().log(
        LogLevel::Info,
        "RecordingEngine",
        "Started recording for camera " + cameraId.value);

    (void)mode;
    return Result<void>::success();
}

Result<void> RecordingEngine::stopRecording(const CameraId& cameraId) {
    std::lock_guard lock(mutex_);
    if (!activeRecordings_.erase(cameraId.value)) {
        return Result<void>::failure("Camera is not recording");
    }

    streamPipeline_->release(cameraId, StreamProfile::Main);
    return Result<void>::success();
}

bool RecordingEngine::isRecording(const CameraId& cameraId) const {
    std::lock_guard lock(mutex_);
    return activeRecordings_.contains(cameraId.value);
}

}  // namespace vms
