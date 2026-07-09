add_library(vms_plugin_sdk STATIC
    src/PluginHost.cpp
)

add_library(Vms::PluginSdk ALIAS vms_plugin_sdk)

target_include_directories(vms_plugin_sdk
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_plugin_sdk
    PUBLIC
        Vms::Core
        Vms::Common
        Vms::Events
)

target_compile_features(vms_plugin_sdk PUBLIC cxx_std_20)
