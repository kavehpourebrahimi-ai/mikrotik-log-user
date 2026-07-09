add_library(vms_api INTERFACE)
add_library(Vms::Api ALIAS vms_api)

target_include_directories(vms_api
    INTERFACE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_api INTERFACE Vms::Core)
