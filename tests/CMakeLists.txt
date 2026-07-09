add_executable(vms_tests
    core/test_types.cpp
    common/test_config.cpp
    common/test_service_registry.cpp
    storage/test_storage.cpp
    camera/test_camera_manager.cpp
    auth/test_auth.cpp
    events/test_events.cpp
)

target_link_libraries(vms_tests
    PRIVATE
        Vms::Core
        Vms::Common
        Vms::Storage
        Vms::Camera
        Vms::Auth
        Vms::Events
        Catch2::Catch2WithMain
)

target_compile_features(vms_tests PRIVATE cxx_std_20)

catch_discover_tests(vms_tests)
