add_library(vms_events STATIC
    src/EventBus.cpp
    src/EventEngine.cpp
)

add_library(Vms::Events ALIAS vms_events)

target_include_directories(vms_events
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_events
    PUBLIC
        Vms::Core
        Vms::Common
)

target_compile_features(vms_events PUBLIC cxx_std_20)
