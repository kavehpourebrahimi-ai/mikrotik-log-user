add_library(vms_auth STATIC
    src/AuthenticationService.cpp
    src/AuthorizationService.cpp
)

add_library(Vms::Auth ALIAS vms_auth)

target_include_directories(vms_auth
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_auth
    PUBLIC
        Vms::Core
        Vms::Common
)

target_compile_features(vms_auth PUBLIC cxx_std_20)
