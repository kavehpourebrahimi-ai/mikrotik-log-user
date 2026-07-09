add_library(vms_storage STATIC
    src/FileCameraRepository.cpp
    src/InMemoryCameraRepository.cpp
    src/LocalStorageProvider.cpp
    src/StorageManager.cpp
)

find_path(VMS_SQLITE3_INCLUDE_DIR sqlite3.h)
find_library(VMS_SQLITE3_LIBRARY sqlite3)

if(VMS_SQLITE3_INCLUDE_DIR AND VMS_SQLITE3_LIBRARY)
    target_sources(vms_storage PRIVATE src/SqliteCameraRepository.cpp)
    target_include_directories(vms_storage PRIVATE ${VMS_SQLITE3_INCLUDE_DIR})
    target_link_libraries(vms_storage PUBLIC ${VMS_SQLITE3_LIBRARY})
    target_compile_definitions(vms_storage PUBLIC VMS_HAS_SQLITE3=1)
endif()

add_library(Vms::Storage ALIAS vms_storage)

target_include_directories(vms_storage
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(vms_storage
    PUBLIC
        Vms::Core
        Vms::Common
        nlohmann_json::nlohmann_json
)

target_compile_features(vms_storage PUBLIC cxx_std_20)
