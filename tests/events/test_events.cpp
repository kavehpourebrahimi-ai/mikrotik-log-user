#include <catch2/catch_test_macros.hpp>

#include "vms/events/EventBus.hpp"
#include "vms/events/EventEngine.hpp"

TEST_CASE("EventBus delivers published events", "[events]") {
    vms::EventBus bus;
    int received = 0;

    bus.subscribe([&](const vms::EventEnvelope& event) {
        REQUIRE(event.type == vms::EventType::MotionDetected);
        ++received;
    });

    vms::EventEnvelope event;
    event.eventId = "evt-1";
    event.type = vms::EventType::MotionDetected;
    bus.publish(event);

    REQUIRE(received == 1);
}

TEST_CASE("EventEngine tracks active alarms", "[events]") {
    vms::EventBus bus;
    vms::EventEngine engine(bus);

    vms::EventEnvelope event;
    event.eventId = "alarm-1";
    event.type = vms::EventType::AlarmRaised;
    REQUIRE(engine.raiseAlarm(event, false).ok());
    REQUIRE(engine.activeAlarms().size() == 1);
    REQUIRE(engine.clearAlarm("alarm-1").ok());
    REQUIRE(engine.activeAlarms().empty());
}
