#include "vms/events/EventEngine.hpp"

#include "vms/common/Logging.hpp"

namespace vms {

EventEngine::EventEngine(IEventBus& eventBus) : eventBus_(eventBus) {}

Result<void> EventEngine::raiseAlarm(
    const EventEnvelope& event,
    bool triggerRecording) {
    {
        std::lock_guard lock(mutex_);
        activeAlarms_.insert(event.eventId);
    }

    eventBus_.publish(event);

    if (triggerRecording) {
        logger().log(
            LogLevel::Info,
            "EventEngine",
            "Recording trigger requested for event " + event.eventId);
    }

    return Result<void>::success();
}

Result<void> EventEngine::clearAlarm(const Uuid& eventId) {
    std::lock_guard lock(mutex_);
    if (!activeAlarms_.erase(eventId)) {
        return Result<void>::failure("Alarm not active: " + eventId);
    }
    return Result<void>::success();
}

std::vector<Uuid> EventEngine::activeAlarms() const {
    std::lock_guard lock(mutex_);
    return {activeAlarms_.begin(), activeAlarms_.end()};
}

}  // namespace vms
