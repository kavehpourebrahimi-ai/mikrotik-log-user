add_library(vms_onvif STATIC
    src/OnvifDiscovery.cpp
)

add_library(Vms::Onvif ALIAS vms_onvif)

target_include_directories(vms_onvif
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_onvif
    PUBLIC
        Vms::Core
        Vms::Common
)

target_compile_features(vms_onvif PUBLIC cxx_std_20)
