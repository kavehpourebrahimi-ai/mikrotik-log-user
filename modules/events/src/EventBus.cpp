#include "vms/events/EventBus.hpp"

namespace vms {

void EventBus::publish(const EventEnvelope& event) {
    std::vector<EventCallback> callbacks;
    {
        std::lock_guard lock(mutex_);
        callbacks = subscribers_;
    }

    for (const auto& callback : callbacks) {
        callback(event);
    }
}

void EventBus::subscribe(EventCallback callback) {
    std::lock_guard lock(mutex_);
    subscribers_.push_back(std::move(callback));
}

}  // namespace vms
