#pragma once

#include <chrono>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

namespace vms {

using Uuid = std::string;
using Timestamp = std::chrono::system_clock::time_point;
using Duration = std::chrono::milliseconds;

/// @brief Strongly typed camera identifier.
struct CameraId {
    Uuid value;

    [[nodiscard]] bool operator==(const CameraId& other) const noexcept {
        return value == other.value;
    }

    [[nodiscard]] bool operator<(const CameraId& other) const noexcept {
        return value < other.value;
    }
};

/// @brief Identifies a logical stream profile on a camera.
enum class StreamProfile : std::uint8_t {
    Main = 0,
    Sub = 1,
    Third = 2
};

/// @brief Supported video codecs for ingest and playback.
enum class VideoCodec : std::uint8_t {
    H264 = 0,
    H265 = 1,
    Mjpeg = 2,
    Unknown = 255
};

/// @brief Transport mode for RTSP/RTP sessions.
enum class TransportProtocol : std::uint8_t {
    Tcp = 0,
    Udp = 1
};

/// @brief Recording trigger modes supported by the recording engine.
enum class RecordingMode : std::uint8_t {
    Continuous = 0,
    Scheduled = 1,
    Motion = 2,
    Event = 3,
    Manual = 4
};

/// @brief Camera health and connectivity state.
enum class CameraStatus : std::uint8_t {
    Unknown = 0,
    Online = 1,
    Offline = 2,
    Degraded = 3,
    Disabled = 4
};

/// @brief Storage backend classification.
enum class StorageBackendType : std::uint8_t {
    Local = 0,
    Raid = 1,
    Iscsi = 2,
    Nas = 3
};

/// @brief Permission scopes enforced by authorization.
enum class Permission : std::uint8_t {
    ViewLive = 0,
    ViewPlayback = 1,
    ExportFootage = 2,
    ManageCameras = 3,
    ManageUsers = 4,
    ManageStorage = 5,
    ManageAlarms = 6,
    ManagePlugins = 7,
    PtzControl = 8,
    SystemAdmin = 9
};

/// @brief Event categories emitted by the event engine.
enum class EventType : std::uint8_t {
    MotionDetected = 0,
    CameraOffline = 1,
    CameraOnline = 2,
    RecordingStarted = 3,
    RecordingStopped = 4,
    AlarmRaised = 5,
    AlarmCleared = 6,
    StorageLow = 7,
    UserLogin = 8,
    PluginEvent = 9
};

/// @brief Describes a discovered or configured network camera.
struct CameraDescriptor {
    CameraId id;
    std::string name;
    std::string host;
    std::uint16_t port{554};
    std::string username;
    std::string password;
    std::string manufacturer;
    std::string model;
    std::string onvifEndpoint;
    std::string mainStreamUri;
    std::string subStreamUri;
    bool ptzSupported{false};
    bool enabled{true};
    CameraStatus status{CameraStatus::Unknown};
};

/// @brief Stream metadata used by live view and recording.
struct StreamInfo {
    CameraId cameraId;
    StreamProfile profile{StreamProfile::Main};
    VideoCodec codec{VideoCodec::Unknown};
    TransportProtocol transport{TransportProtocol::Tcp};
    std::string uri;
    std::uint32_t width{0};
    std::uint32_t height{0};
    std::uint32_t frameRate{0};
};

/// @brief A contiguous recorded segment on storage.
struct RecordingSegment {
    Uuid segmentId;
    CameraId cameraId;
    Timestamp startTime{};
    Timestamp endTime{};
    std::string storagePath;
    std::uint64_t sizeBytes{0};
    VideoCodec codec{VideoCodec::Unknown};
    RecordingMode mode{RecordingMode::Continuous};
};

/// @brief User-defined playback bookmark.
struct Bookmark {
    Uuid bookmarkId;
    CameraId cameraId;
    Timestamp timestamp{};
    std::string label;
    std::string createdBy;
};

/// @brief Storage volume descriptor.
struct StorageVolume {
    Uuid volumeId;
    std::string mountPath;
    StorageBackendType backend{StorageBackendType::Local};
    std::uint64_t totalBytes{0};
    std::uint64_t freeBytes{0};
    bool writable{true};
};

/// @brief Role definition for RBAC.
struct Role {
    Uuid roleId;
    std::string name;
    std::vector<Permission> permissions;
};

/// @brief Authenticated principal.
struct User {
    Uuid userId;
    std::string username;
    std::string displayName;
    std::vector<Uuid> roleIds;
    bool enabled{true};
};

/// @brief System event envelope.
struct EventEnvelope {
    Uuid eventId;
    EventType type{EventType::PluginEvent};
    Timestamp timestamp{};
    CameraId cameraId;
    std::string source;
    std::string message;
    std::string payloadJson;
};

/// @brief Result type for fallible operations without exceptions on hot paths.
template <typename T>
struct Result {
    std::optional<T> value;
    std::string error;

    [[nodiscard]] bool ok() const noexcept { return value.has_value(); }

    [[nodiscard]] static Result success(T val) {
        return Result{std::move(val), {}};
    }

    [[nodiscard]] static Result failure(std::string err) {
        return Result{std::nullopt, std::move(err)};
    }
};

template <>
struct Result<void> {
    std::string error;

    [[nodiscard]] bool ok() const noexcept { return error.empty(); }

    [[nodiscard]] static Result success() { return Result{}; }

    [[nodiscard]] static Result failure(std::string err) {
        return Result{std::move(err)};
    }
};

}  // namespace vms
