#include <catch2/catch_test_macros.hpp>

#include <chrono>
#include <filesystem>
#include <thread>

#include "vms/recording/RecordingEngine.hpp"
#include "vms/storage/LocalStorageProvider.hpp"
#include "vms/storage/StorageManager.hpp"
#include "vms/streaming/StreamPipeline.hpp"

TEST_CASE("RecordingEngine creates recording file and stops", "[recording]") {
    const auto root = std::filesystem::temp_directory_path() / "vms-recording-test";
    std::filesystem::remove_all(root);

    auto storageManager = std::make_shared<vms::StorageManager>();
    auto provider = std::make_shared<vms::LocalStorageProvider>(root);
    REQUIRE(storageManager->registerProvider("local", provider).ok());

    auto streamPipeline = std::make_shared<vms::StreamPipeline>();
    vms::RecordingEngine engine(storageManager, streamPipeline);
    const vms::CameraId cameraId{"record-cam-1"};

    REQUIRE(engine.startRecording(cameraId, vms::RecordingMode::Continuous).ok());
    REQUIRE(engine.isRecording(cameraId));

    std::this_thread::sleep_for(std::chrono::milliseconds(1100));

    REQUIRE(engine.stopRecording(cameraId).ok());
    REQUIRE_FALSE(engine.isRecording(cameraId));

    const auto cameraDir = root / cameraId.value;
    REQUIRE(std::filesystem::exists(cameraDir));
    bool hasFile = false;
    for (const auto& entry : std::filesystem::directory_iterator(cameraDir)) {
        if (entry.path().extension() == ".vmslog") {
            hasFile = true;
            break;
        }
    }
    REQUIRE(hasFile);

    std::filesystem::remove_all(root);
}
