add_library(vms_camera STATIC
    src/CameraManager.cpp
)

add_library(Vms::Camera ALIAS vms_camera)

target_include_directories(vms_camera
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_camera
    PUBLIC
        Vms::Core
        Vms::Common
        Vms::Storage
)

target_compile_features(vms_camera PUBLIC cxx_std_20)
