#pragma once

/// @file WebSocketApi.hpp
/// @brief WebSocket notification contract (Phase 2: gateway binding).

#include <string>
#include <vector>

namespace vms::api {

/// @brief WebSocket channels published to connected clients.
enum class WebSocketChannel : std::uint8_t {
    Events = 0,
    CameraStatus = 1,
    Alarms = 2,
    StorageHealth = 3,
    RecordingState = 4
};

/// @brief Returns supported WebSocket channels.
[[nodiscard]] inline std::vector<std::string> webSocketChannels() {
    return {
        "events",
        "camera.status",
        "alarms",
        "storage.health",
        "recording.state"};
}

}  // namespace vms::api
