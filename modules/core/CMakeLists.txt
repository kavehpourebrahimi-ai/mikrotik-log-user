add_library(vms_core INTERFACE)
add_library(Vms::Core ALIAS vms_core)

target_include_directories(vms_core
    INTERFACE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_features(vms_core INTERFACE cxx_std_20)
