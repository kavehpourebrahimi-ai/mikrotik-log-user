add_library(vms_recording STATIC
    src/RecordingEngine.cpp
)

add_library(Vms::Recording ALIAS vms_recording)

target_include_directories(vms_recording
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_recording
    PUBLIC
        Vms::Core
        Vms::Common
        Vms::Storage
        Vms::Streaming
)

target_compile_features(vms_recording PUBLIC cxx_std_20)
