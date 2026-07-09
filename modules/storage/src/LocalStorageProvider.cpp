#include "vms/storage/LocalStorageProvider.hpp"

#include "vms/common/Uuid.hpp"

#include <chrono>
#include <iomanip>
#include <sstream>
#include <system_error>

namespace vms {
namespace {

std::string formatTimestamp(Timestamp timestamp) {
    const auto time = std::chrono::system_clock::to_time_t(timestamp);
    std::ostringstream stream;
    stream << std::put_time(std::gmtime(&time), "%Y%m%dT%H%M%SZ");
    return stream.str();
}

}  // namespace

LocalStorageProvider::LocalStorageProvider(std::filesystem::path rootPath)
    : rootPath_(std::move(rootPath)), volumeId_(generateUuid()) {
    std::error_code ec;
    std::filesystem::create_directories(rootPath_, ec);
}

Result<StorageVolume> LocalStorageProvider::describe() const {
    std::error_code ec;
    const auto space = std::filesystem::space(rootPath_, ec);
    if (ec) {
        return Result<StorageVolume>::failure(ec.message());
    }

    StorageVolume volume;
    volume.volumeId = volumeId_;
    volume.mountPath = rootPath_.string();
    volume.backend = StorageBackendType::Local;
    volume.totalBytes = static_cast<std::uint64_t>(space.capacity);
    volume.freeBytes = static_cast<std::uint64_t>(space.available);
    volume.writable = true;
    return Result<StorageVolume>::success(volume);
}

Result<void> LocalStorageProvider::verify(const std::string& path) const {
    const std::filesystem::path fullPath = rootPath_ / path;
    if (!std::filesystem::exists(fullPath)) {
        return Result<void>::failure("Path does not exist: " + fullPath.string());
    }
    return Result<void>::success();
}

Result<std::string> LocalStorageProvider::allocateSegmentPath(
    const CameraId& cameraId,
    Timestamp startTime) {
    const auto cameraDir = rootPath_ / cameraId.value;
    std::error_code ec;
    std::filesystem::create_directories(cameraDir, ec);
    if (ec) {
        return Result<std::string>::failure(ec.message());
    }

    const auto fileName = formatTimestamp(startTime) + ".vms";
    const auto relative = std::filesystem::path(cameraId.value) / fileName;
    return Result<std::string>::success(relative.string());
}

}  // namespace vms
