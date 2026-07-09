add_library(vms_streaming STATIC
    src/StreamPipeline.cpp
)

add_library(Vms::Streaming ALIAS vms_streaming)

target_include_directories(vms_streaming
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_streaming
    PUBLIC
        Vms::Core
        Vms::Common
)

target_compile_features(vms_streaming PUBLIC cxx_std_20)
