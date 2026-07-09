add_library(vms_common STATIC
    src/Config.cpp
    src/Logging.cpp
    src/ServiceRegistry.cpp
    src/Uuid.cpp
)

add_library(Vms::Common ALIAS vms_common)

target_include_directories(vms_common
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_link_libraries(vms_common
    PUBLIC
        Vms::Core
)

target_compile_features(vms_common PUBLIC cxx_std_20)
