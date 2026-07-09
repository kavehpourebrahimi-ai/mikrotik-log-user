#include "vms/recording/RecordingEngine.hpp"

#include "vms/common/Logging.hpp"

#include <chrono>
#include <filesystem>
#include <fstream>

namespace vms {
namespace {

std::string makeRecordingPath(const std::string& root, const CameraId& cameraId) {
    const auto now = std::chrono::system_clock::now();
    const auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()).count();
    std::filesystem::path path = std::filesystem::path(root) / cameraId.value;
    std::filesystem::create_directories(path);
    path /= "segment-" + std::to_string(millis) + ".vmslog";
    return path.string();
}

}  // namespace

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
        "rtsp://recording-placeholder/" + cameraId.value,
        0,
        0,
        0};

    const auto startResult = session->start(stream);
    if (!startResult.ok()) {
        return startResult;
    }

    const auto volumes = storageManager_->listVolumes();
    if (volumes.empty()) {
        return Result<void>::failure("No storage volumes are available");
    }
    const auto recordingPath = makeRecordingPath(volumes.front().mountPath, cameraId);

    auto worker = std::make_unique<RecordingWorker>();
    worker->running.store(true);
    worker->filePath = recordingPath;
    worker->thread = std::thread([cameraId, mode, path = worker->filePath, running = &worker->running]() {
        std::ofstream output(path, std::ios::out | std::ios::trunc);
        if (!output.is_open()) {
            return;
        }
        output << "camera_id=" << cameraId.value << '\n';
        output << "mode=" << static_cast<int>(mode) << '\n';
        output << "start_epoch_ms="
               << std::chrono::duration_cast<std::chrono::milliseconds>(
                      std::chrono::system_clock::now().time_since_epoch())
                      .count()
               << '\n';

        while (running->load()) {
            output << "tick_ms="
                   << std::chrono::duration_cast<std::chrono::milliseconds>(
                          std::chrono::system_clock::now().time_since_epoch())
                          .count()
                   << '\n';
            output.flush();
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }

        output << "stop_epoch_ms="
               << std::chrono::duration_cast<std::chrono::milliseconds>(
                      std::chrono::system_clock::now().time_since_epoch())
                      .count()
               << '\n';
        output.flush();
    });

    {
        std::lock_guard lock(mutex_);
        if (activeRecordings_.contains(cameraId.value)) {
            worker->running.store(false);
            if (worker->thread.joinable()) {
                worker->thread.join();
            }
            return Result<void>::failure("Camera is already recording");
        }
        activeRecordings_.insert(cameraId.value);
        workers_[cameraId.value] = std::move(worker);
    }

    logger().log(
        LogLevel::Info,
        "RecordingEngine",
        "Started recording for camera " + cameraId.value + " -> " + recordingPath);

    return Result<void>::success();
}

Result<void> RecordingEngine::stopRecording(const CameraId& cameraId) {
    std::unique_ptr<RecordingWorker> worker;
    {
        std::lock_guard lock(mutex_);
        if (!activeRecordings_.erase(cameraId.value)) {
            return Result<void>::failure("Camera is not recording");
        }
        worker = std::move(workers_[cameraId.value]);
        workers_.erase(cameraId.value);
    }

    worker->running.store(false);
    if (worker->thread.joinable()) {
        worker->thread.join();
    }

    streamPipeline_->release(cameraId, StreamProfile::Main);
    return Result<void>::success();
}

bool RecordingEngine::isRecording(const CameraId& cameraId) const {
    std::lock_guard lock(mutex_);
    return activeRecordings_.contains(cameraId.value);
}

}  // namespace vms
