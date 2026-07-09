#pragma once

#include <atomic>
#include <memory>
#include <mutex>
#include <thread>
#include <unordered_map>
#include <unordered_set>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief Recording engine with pass-through main stream writes (no transcoding).
class RecordingEngine final : public IRecordingEngine {
public:
    RecordingEngine(
        std::shared_ptr<IStorageManager> storageManager,
        std::shared_ptr<IStreamPipeline> streamPipeline);

    Result<void> startRecording(
        const CameraId& cameraId,
        RecordingMode mode) override;

    Result<void> stopRecording(const CameraId& cameraId) override;
    [[nodiscard]] bool isRecording(const CameraId& cameraId) const override;

private:
    struct RecordingWorker {
        std::atomic<bool> running{false};
        std::thread thread;
        std::string filePath;
    };

    std::shared_ptr<IStorageManager> storageManager_;
    std::shared_ptr<IStreamPipeline> streamPipeline_;
    mutable std::mutex mutex_;
    std::unordered_set<std::string> activeRecordings_;
    std::unordered_map<std::string, std::unique_ptr<RecordingWorker>> workers_;
};

}  // namespace vms
