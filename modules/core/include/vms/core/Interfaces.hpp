#pragma once

#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "vms/core/Types.hpp"

namespace vms {

/// @brief Callback invoked when a camera status changes.
using CameraStatusCallback = std::function<void(const CameraId&, CameraStatus)>;

/// @brief Callback invoked when a system event is published.
using EventCallback = std::function<void(const EventEnvelope&)>;

/// @brief Callback invoked when encoded media is available.
using MediaFrameCallback = std::function<void(
    const CameraId&,
    StreamProfile,
    const std::uint8_t* data,
    std::size_t size,
    Timestamp captureTime)>;

/// @brief Repository for camera configuration persistence.
class ICameraRepository {
public:
    virtual ~ICameraRepository() = default;

  /// @brief Returns all configured cameras.
    [[nodiscard]] virtual std::vector<CameraDescriptor> list() const = 0;

  /// @brief Returns a camera by identifier.
    [[nodiscard]] virtual Result<CameraDescriptor> get(const CameraId& id) const = 0;

  /// @brief Persists a new or updated camera descriptor.
    virtual Result<void> upsert(const CameraDescriptor& camera) = 0;

  /// @brief Removes a camera from the repository.
    virtual Result<void> remove(const CameraId& id) = 0;
};

/// @brief Manages camera lifecycle, health, and stream metadata.
class ICameraManager {
public:
    virtual ~ICameraManager() = default;

  /// @brief Registers a status change listener.
    virtual void onStatusChanged(CameraStatusCallback callback) = 0;

  /// @brief Returns stream metadata for the requested profile.
    [[nodiscard]] virtual Result<StreamInfo> getStreamInfo(
        const CameraId& id,
        StreamProfile profile) const = 0;

  /// @brief Enables or disables a camera without deleting configuration.
    virtual Result<void> setEnabled(const CameraId& id, bool enabled) = 0;

  /// @brief Forces a reconnect attempt for a camera ingest session.
    virtual Result<void> reconnect(const CameraId& id) = 0;
};

/// @brief Discovers ONVIF devices on the local network.
class IOnvifDiscovery {
public:
    virtual ~IOnvifDiscovery() = default;

  /// @brief Starts WS-Discovery probe for the given timeout.
    [[nodiscard]] virtual Result<std::vector<CameraDescriptor>> discover(
        Duration timeout) = 0;

  /// @brief Resolves stream URIs and capabilities for a discovered device.
    [[nodiscard]] virtual Result<CameraDescriptor> configure(
        const CameraDescriptor& discovered,
        std::string_view username,
        std::string_view password) = 0;
};

/// @brief RTSP ingest and fan-out session.
class IStreamSession {
public:
    virtual ~IStreamSession() = default;

  /// @brief Opens an RTSP session for the given stream.
    virtual Result<void> start(const StreamInfo& stream) = 0;

  /// @brief Stops the active session and releases resources.
    virtual void stop() = 0;

  /// @brief Returns whether the session is actively receiving media.
    [[nodiscard]] virtual bool isActive() const = 0;

  /// @brief Subscribes to encoded media frames.
    virtual void onFrame(MediaFrameCallback callback) = 0;
};

/// @brief Factory for stream sessions keyed by camera and profile.
class IStreamPipeline {
public:
    virtual ~IStreamPipeline() = default;

  /// @brief Acquires or creates a shared ingest session.
    [[nodiscard]] virtual std::shared_ptr<IStreamSession> acquire(
        const CameraId& cameraId,
        StreamProfile profile) = 0;

  /// @brief Releases a previously acquired session reference.
    virtual void release(
        const CameraId& cameraId,
        StreamProfile profile) = 0;
};

/// @brief Writes original main-stream bitstream without transcoding.
class IRecordingWriter {
public:
    virtual ~IRecordingWriter() = default;

  /// @brief Opens a new segment for append-only recording.
    virtual Result<void> openSegment(
        const CameraId& cameraId,
        RecordingMode mode,
        Timestamp startTime) = 0;

  /// @brief Appends an encoded access unit to the active segment.
    virtual Result<void> writeFrame(
        const std::uint8_t* data,
        std::size_t size,
        Timestamp captureTime,
        bool isKeyFrame) = 0;

  /// @brief Finalizes the active segment and returns metadata.
    [[nodiscard]] virtual Result<RecordingSegment> closeSegment() = 0;
};

/// @brief Orchestrates per-camera recording policies.
class IRecordingEngine {
public:
    virtual ~IRecordingEngine() = default;

  /// @brief Starts recording for a camera using the configured mode.
    virtual Result<void> startRecording(
        const CameraId& cameraId,
        RecordingMode mode) = 0;

  /// @brief Stops active recording for a camera.
    virtual Result<void> stopRecording(const CameraId& cameraId) = 0;

  /// @brief Returns whether a camera is actively recording.
    [[nodiscard]] virtual bool isRecording(const CameraId& cameraId) const = 0;
};

/// @brief Reads recorded segments for timeline playback.
class IPlaybackEngine {
public:
    virtual ~IPlaybackEngine() = default;

  /// @brief Returns segments intersecting the requested time range.
    [[nodiscard]] virtual Result<std::vector<RecordingSegment>> querySegments(
        const CameraId& cameraId,
        Timestamp from,
        Timestamp to) const = 0;

  /// @brief Opens a playback session at the requested timestamp.
    virtual Result<void> seek(const CameraId& cameraId, Timestamp position) = 0;

  /// @brief Subscribes to playback frames after seek.
    virtual void onPlaybackFrame(MediaFrameCallback callback) = 0;
};

/// @brief Abstract storage backend (local, RAID, iSCSI, NAS).
class IStorageProvider {
public:
    virtual ~IStorageProvider() = default;

  /// @brief Returns volume metadata for this provider.
    [[nodiscard]] virtual Result<StorageVolume> describe() const = 0;

  /// @brief Verifies read/write integrity for a path.
    [[nodiscard]] virtual Result<void> verify(const std::string& path) const = 0;

  /// @brief Resolves a writable path for a new recording segment.
    [[nodiscard]] virtual Result<std::string> allocateSegmentPath(
        const CameraId& cameraId,
        Timestamp startTime) = 0;
};

/// @brief Manages retention, volume selection, and integrity checks.
class IStorageManager {
public:
    virtual ~IStorageManager() = default;

  /// @brief Registers a storage provider.
    virtual Result<void> registerProvider(
        const Uuid& providerId,
        std::shared_ptr<IStorageProvider> provider) = 0;

  /// @brief Returns all known volumes.
    [[nodiscard]] virtual std::vector<StorageVolume> listVolumes() const = 0;

  /// @brief Applies retention policy and deletes expired segments.
    virtual Result<std::uint64_t> enforceRetention(Duration maxAge) = 0;
};

/// @brief Issues and validates access tokens.
class IAuthenticationService {
public:
    virtual ~IAuthenticationService() = default;

  /// @brief Authenticates credentials and returns a session token.
    [[nodiscard]] virtual Result<std::string> authenticate(
        std::string_view username,
        std::string_view password) const = 0;

  /// @brief Validates a session token and returns the associated user.
    [[nodiscard]] virtual Result<User> validateToken(std::string_view token) const = 0;
};

/// @brief Evaluates RBAC permissions for a principal.
class IAuthorizationService {
public:
    virtual ~IAuthorizationService() = default;

  /// @brief Returns whether the user has the requested permission.
    [[nodiscard]] virtual bool hasPermission(
        const User& user,
        Permission permission) const = 0;

  /// @brief Returns all effective permissions for a user.
    [[nodiscard]] virtual std::vector<Permission> listPermissions(
        const User& user) const = 0;
};

/// @brief Publishes and subscribes to domain events.
class IEventBus {
public:
    virtual ~IEventBus() = default;

  /// @brief Publishes an event to all subscribers.
    virtual void publish(const EventEnvelope& event) = 0;

  /// @brief Subscribes to all events.
    virtual void subscribe(EventCallback callback) = 0;
};

/// @brief Correlates alarms and recording triggers.
class IEventEngine {
public:
    virtual ~IEventEngine() = default;

  /// @brief Raises an alarm and optionally triggers recording.
    virtual Result<void> raiseAlarm(
        const EventEnvelope& event,
        bool triggerRecording) = 0;

  /// @brief Clears an active alarm by event identifier.
    virtual Result<void> clearAlarm(const Uuid& eventId) = 0;
};

/// @brief Host interface for dynamically loaded plugins.
class IPlugin {
public:
    virtual ~IPlugin() = default;

  /// @brief Returns the plugin identifier.
    [[nodiscard]] virtual std::string id() const = 0;

  /// @brief Initializes the plugin with host services.
    virtual Result<void> initialize(IEventBus& eventBus) = 0;

  /// @brief Shuts down the plugin and releases resources.
    virtual void shutdown() = 0;
};

/// @brief Loads and manages plugin lifecycle.
class IPluginHost {
public:
    virtual ~IPluginHost() = default;

  /// @brief Loads a plugin from the given module path.
    virtual Result<void> load(const std::string& modulePath) = 0;

  /// @brief Unloads a plugin by identifier.
    virtual Result<void> unload(const std::string& pluginId) = 0;

  /// @brief Returns identifiers of loaded plugins.
    [[nodiscard]] virtual std::vector<std::string> loadedPlugins() const = 0;
};

}  // namespace vms
