#include <catch2/catch_test_macros.hpp>

#include "vms/camera/CameraManager.hpp"
#include "vms/storage/InMemoryCameraRepository.hpp"

TEST_CASE("CameraManager resolves stream profiles", "[camera]") {
    auto repository = std::make_shared<vms::InMemoryCameraRepository>();
    vms::CameraDescriptor camera;
    camera.id = vms::CameraId{"cam-1"};
    camera.name = "Lobby";
    camera.mainStreamUri = "rtsp://10.0.0.10/main";
    camera.subStreamUri = "rtsp://10.0.0.10/sub";
    REQUIRE(repository->upsert(camera).ok());

    vms::CameraManager manager(repository);
    const auto mainStream = manager.getStreamInfo(camera.id, vms::StreamProfile::Main);
    REQUIRE(mainStream.ok());
    REQUIRE(mainStream.value->uri == camera.mainStreamUri);

    const auto subStream = manager.getStreamInfo(camera.id, vms::StreamProfile::Sub);
    REQUIRE(subStream.ok());
    REQUIRE(subStream.value->uri == camera.subStreamUri);
}
