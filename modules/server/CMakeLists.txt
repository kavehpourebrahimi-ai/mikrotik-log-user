add_executable(vms_server
    src/main.cpp
    src/ServerHost.cpp
)

target_include_directories(vms_server
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(vms_server
    PRIVATE
        Vms::Core
        Vms::Common
        Vms::Storage
        Vms::Camera
        Vms::Auth
        Vms::Events
        Vms::Streaming
        Vms::Recording
        Vms::Playback
        Vms::Onvif
        Vms::PluginSdk
)

target_compile_features(vms_server PRIVATE cxx_std_20)
