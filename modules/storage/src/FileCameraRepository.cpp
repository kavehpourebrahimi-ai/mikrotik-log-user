#include "vms/storage/FileCameraRepository.hpp"

#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>

namespace vms {
namespace {
using json = nlohmann::json;

int toStatusInt(CameraStatus status) {
    return static_cast<int>(status);
}

CameraStatus fromStatusInt(int value) {
    switch (value) {
        case 1:
            return CameraStatus::Online;
        case 2:
            return CameraStatus::Offline;
        case 3:
            return CameraStatus::Degraded;
        case 4:
            return CameraStatus::Disabled;
        default:
            return CameraStatus::Unknown;
    }
}
}  // namespace

FileCameraRepository::FileCameraRepository(std::string filePath)
    : filePath_(std::move(filePath)) {
    (void)loadFromDisk();
}

std::vector<CameraDescriptor> FileCameraRepository::list() const {
    std::lock_guard lock(mutex_);
    std::vector<CameraDescriptor> result;
    result.reserve(cameras_.size());
    for (const auto& [_, camera] : cameras_) {
        result.push_back(camera);
    }
    return result;
}

Result<CameraDescriptor> FileCameraRepository::get(const CameraId& id) const {
    std::lock_guard lock(mutex_);
    const auto it = cameras_.find(id.value);
    if (it == cameras_.end()) {
        return Result<CameraDescriptor>::failure("Camera not found: " + id.value);
    }
    return Result<CameraDescriptor>::success(it->second);
}

Result<void> FileCameraRepository::upsert(const CameraDescriptor& camera) {
    if (camera.id.value.empty()) {
        return Result<void>::failure("Camera id is required");
    }

    std::lock_guard lock(mutex_);
    cameras_[camera.id.value] = camera;
    return persistToDisk();
}

Result<void> FileCameraRepository::remove(const CameraId& id) {
    std::lock_guard lock(mutex_);
    if (!cameras_.erase(id.value)) {
        return Result<void>::failure("Camera not found: " + id.value);
    }
    return persistToDisk();
}

Result<void> FileCameraRepository::loadFromDisk() {
    std::lock_guard lock(mutex_);
    if (!std::filesystem::exists(filePath_)) {
        return Result<void>::success();
    }

    std::ifstream input(filePath_);
    if (!input.is_open()) {
        return Result<void>::failure("Failed to open camera db file: " + filePath_);
    }

    json root;
    try {
        input >> root;
    } catch (...) {
        return Result<void>::failure("Invalid camera db json format");
    }

    if (!root.is_array()) {
        return Result<void>::failure("Camera db root must be an array");
    }

    cameras_.clear();
    for (const auto& item : root) {
        CameraDescriptor camera;
        camera.id.value = item.value("id", "");
        if (camera.id.value.empty()) {
            continue;
        }
        camera.name = item.value("name", "");
        camera.host = item.value("host", "");
        camera.port = static_cast<std::uint16_t>(item.value("port", 554));
        camera.username = item.value("username", "");
        camera.password = item.value("password", "");
        camera.manufacturer = item.value("manufacturer", "");
        camera.model = item.value("model", "");
        camera.onvifEndpoint = item.value("onvifEndpoint", "");
        camera.mainStreamUri = item.value("mainStreamUri", "");
        camera.subStreamUri = item.value("subStreamUri", "");
        camera.ptzSupported = item.value("ptzSupported", false);
        camera.enabled = item.value("enabled", true);
        camera.status = fromStatusInt(item.value("status", 0));
        cameras_[camera.id.value] = std::move(camera);
    }

    return Result<void>::success();
}

Result<void> FileCameraRepository::persistToDisk() const {
    std::filesystem::create_directories(std::filesystem::path(filePath_).parent_path());

    json root = json::array();
    for (const auto& [_, camera] : cameras_) {
        root.push_back({
            {"id", camera.id.value},
            {"name", camera.name},
            {"host", camera.host},
            {"port", camera.port},
            {"username", camera.username},
            {"password", camera.password},
            {"manufacturer", camera.manufacturer},
            {"model", camera.model},
            {"onvifEndpoint", camera.onvifEndpoint},
            {"mainStreamUri", camera.mainStreamUri},
            {"subStreamUri", camera.subStreamUri},
            {"ptzSupported", camera.ptzSupported},
            {"enabled", camera.enabled},
            {"status", toStatusInt(camera.status)},
        });
    }

    std::ofstream output(filePath_, std::ios::trunc);
    if (!output.is_open()) {
        return Result<void>::failure("Failed to write camera db file: " + filePath_);
    }

    output << root.dump(2);
    return Result<void>::success();
}

}  // namespace vms
