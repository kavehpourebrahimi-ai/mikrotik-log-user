add_library(vms_playback STATIC
    src/PlaybackEngine.cpp
)

add_library(Vms::Playback ALIAS vms_playback)

target_include_directories(vms_playback
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_playback
    PUBLIC
        Vms::Core
        Vms::Common
        Vms::Storage
)

target_compile_features(vms_playback PUBLIC cxx_std_20)
