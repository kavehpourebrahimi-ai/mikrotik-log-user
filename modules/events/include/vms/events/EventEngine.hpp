#pragma once

#include <mutex>
#include <unordered_set>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief Correlates alarms and optional recording triggers.
class EventEngine final : public IEventEngine {
public:
    explicit EventEngine(IEventBus& eventBus);

    Result<void> raiseAlarm(
        const EventEnvelope& event,
        bool triggerRecording) override;

    Result<void> clearAlarm(const Uuid& eventId) override;

    [[nodiscard]] std::vector<Uuid> activeAlarms() const;

private:
    IEventBus& eventBus_;
    mutable std::mutex mutex_;
    std::unordered_set<std::string> activeAlarms_;
};

}  // namespace vms
