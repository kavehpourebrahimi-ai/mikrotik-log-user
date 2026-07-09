#include <catch2/catch_test_macros.hpp>

#include <filesystem>

#include "vms/storage/LocalStorageProvider.hpp"
#include "vms/storage/StorageManager.hpp"

TEST_CASE("LocalStorageProvider allocates segment paths", "[storage]") {
    const auto root = std::filesystem::temp_directory_path() / "vms-storage-test";
    std::filesystem::remove_all(root);

    vms::LocalStorageProvider provider(root);
    const auto volume = provider.describe();
    REQUIRE(volume.ok());
    REQUIRE(volume.value->backend == vms::StorageBackendType::Local);

    const vms::CameraId cameraId{"cam-001"};
    const auto path = provider.allocateSegmentPath(
        cameraId,
        std::chrono::system_clock::now());
    REQUIRE(path.ok());
    REQUIRE(path.value->find("cam-001") != std::string::npos);

    vms::StorageManager manager;
    manager.registerProvider("local", std::make_shared<vms::LocalStorageProvider>(root));
    REQUIRE(manager.listVolumes().size() == 1);

    std::filesystem::remove_all(root);
}
