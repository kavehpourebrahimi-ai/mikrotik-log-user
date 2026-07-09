add_executable(vms_client
    src/main.cpp
    src/ClientApp.cpp
)

target_include_directories(vms_client
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(vms_client
    PRIVATE
        Vms::Core
        Vms::Common
        Vms::Api
)

target_compile_features(vms_client PRIVATE cxx_std_20)
