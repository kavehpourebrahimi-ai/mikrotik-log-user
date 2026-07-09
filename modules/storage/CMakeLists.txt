add_library(vms_storage STATIC
    src/InMemoryCameraRepository.cpp
    src/LocalStorageProvider.cpp
    src/StorageManager.cpp
)

add_library(Vms::Storage ALIAS vms_storage)

target_include_directories(vms_storage
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_storage
    PUBLIC
        Vms::Core
        Vms::Common
)

target_compile_features(vms_storage PUBLIC cxx_std_20)
