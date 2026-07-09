#pragma once

#include <mutex>
#include <vector>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief In-process publish/subscribe event bus.
class EventBus final : public IEventBus {
public:
    void publish(const EventEnvelope& event) override;
    void subscribe(EventCallback callback) override;

private:
    mutable std::mutex mutex_;
    std::vector<EventCallback> subscribers_;
};

}  // namespace vms
