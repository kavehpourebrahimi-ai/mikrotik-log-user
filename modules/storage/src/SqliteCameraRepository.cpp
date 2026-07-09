#include "vms/storage/SqliteCameraRepository.hpp"

#include <sqlite3.h>

namespace vms {
namespace {

Result<void> execSql(sqlite3* db, const char* sql) {
    char* error = nullptr;
    if (sqlite3_exec(db, sql, nullptr, nullptr, &error) != SQLITE_OK) {
        const std::string message = error ? error : "Unknown SQLite error";
        sqlite3_free(error);
        return Result<void>::failure(message);
    }
    return Result<void>::success();
}

CameraStatus parseStatus(int value) {
    switch (value) {
        case 1:
            return CameraStatus::Online;
        case 2:
            return CameraStatus::Offline;
        case 3:
            return CameraStatus::Degraded;
        case 4:
            return CameraStatus::Disabled;
        default:
            return CameraStatus::Unknown;
    }
}

int toStatusInt(CameraStatus status) {
    return static_cast<int>(status);
}

std::string columnText(sqlite3_stmt* statement, int column) {
    const auto* text = sqlite3_column_text(statement, column);
    return text ? reinterpret_cast<const char*>(text) : "";
}

}  // namespace

SqliteCameraRepository::SqliteCameraRepository(std::string databasePath)
    : databasePath_(std::move(databasePath)) {
    (void)open();
    (void)initializeSchema();
}

SqliteCameraRepository::~SqliteCameraRepository() {
    close();
}

Result<void> SqliteCameraRepository::open() {
    if (db_ != nullptr) {
        return Result<void>::success();
    }
    if (sqlite3_open_v2(
            databasePath_.c_str(),
            &db_,
            SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_FULLMUTEX,
            nullptr)
        != SQLITE_OK) {
        const auto message = std::string(sqlite3_errmsg(db_));
        close();
        return Result<void>::failure("Failed to open SQLite DB: " + message);
    }
    return Result<void>::success();
}

void SqliteCameraRepository::close() {
    if (db_ != nullptr) {
        sqlite3_close(db_);
        db_ = nullptr;
    }
}

Result<void> SqliteCameraRepository::initializeSchema() {
    std::lock_guard lock(mutex_);
    const auto openResult = open();
    if (!openResult.ok()) {
        return openResult;
    }

    return execSql(
        db_,
        "CREATE TABLE IF NOT EXISTS cameras ("
        "id TEXT PRIMARY KEY,"
        "name TEXT NOT NULL,"
        "host TEXT NOT NULL,"
        "port INTEGER NOT NULL DEFAULT 554,"
        "username TEXT,"
        "password TEXT,"
        "manufacturer TEXT,"
        "model TEXT,"
        "onvif_endpoint TEXT,"
        "main_stream_uri TEXT,"
        "sub_stream_uri TEXT,"
        "ptz_supported INTEGER NOT NULL DEFAULT 0,"
        "enabled INTEGER NOT NULL DEFAULT 1,"
        "status INTEGER NOT NULL DEFAULT 0"
        ");");
}

std::vector<CameraDescriptor> SqliteCameraRepository::list() const {
    std::lock_guard lock(mutex_);
    std::vector<CameraDescriptor> cameras;
    if (db_ == nullptr) {
        return cameras;
    }

    sqlite3_stmt* statement = nullptr;
    const char* sql =
        "SELECT id,name,host,port,username,password,manufacturer,model,onvif_endpoint,"
        "main_stream_uri,sub_stream_uri,ptz_supported,enabled,status FROM cameras;";
    if (sqlite3_prepare_v2(db_, sql, -1, &statement, nullptr) != SQLITE_OK) {
        return cameras;
    }

    while (sqlite3_step(statement) == SQLITE_ROW) {
        CameraDescriptor camera;
        camera.id.value = columnText(statement, 0);
        camera.name = columnText(statement, 1);
        camera.host = columnText(statement, 2);
        camera.port = static_cast<std::uint16_t>(sqlite3_column_int(statement, 3));
        camera.username = columnText(statement, 4);
        camera.password = columnText(statement, 5);
        camera.manufacturer = columnText(statement, 6);
        camera.model = columnText(statement, 7);
        camera.onvifEndpoint = columnText(statement, 8);
        camera.mainStreamUri = columnText(statement, 9);
        camera.subStreamUri = columnText(statement, 10);
        camera.ptzSupported = sqlite3_column_int(statement, 11) != 0;
        camera.enabled = sqlite3_column_int(statement, 12) != 0;
        camera.status = parseStatus(sqlite3_column_int(statement, 13));
        cameras.push_back(std::move(camera));
    }

    sqlite3_finalize(statement);
    return cameras;
}

Result<CameraDescriptor> SqliteCameraRepository::get(const CameraId& id) const {
    std::lock_guard lock(mutex_);
    if (db_ == nullptr) {
        return Result<CameraDescriptor>::failure("Database is not available");
    }

    sqlite3_stmt* statement = nullptr;
    const char* sql =
        "SELECT id,name,host,port,username,password,manufacturer,model,onvif_endpoint,"
        "main_stream_uri,sub_stream_uri,ptz_supported,enabled,status FROM cameras WHERE id=?1;";
    if (sqlite3_prepare_v2(db_, sql, -1, &statement, nullptr) != SQLITE_OK) {
        return Result<CameraDescriptor>::failure("Failed to prepare get query");
    }

    sqlite3_bind_text(statement, 1, id.value.c_str(), -1, SQLITE_TRANSIENT);
    if (sqlite3_step(statement) != SQLITE_ROW) {
        sqlite3_finalize(statement);
        return Result<CameraDescriptor>::failure("Camera not found: " + id.value);
    }

    CameraDescriptor camera;
    camera.id.value = columnText(statement, 0);
    camera.name = columnText(statement, 1);
    camera.host = columnText(statement, 2);
    camera.port = static_cast<std::uint16_t>(sqlite3_column_int(statement, 3));
    camera.username = columnText(statement, 4);
    camera.password = columnText(statement, 5);
    camera.manufacturer = columnText(statement, 6);
    camera.model = columnText(statement, 7);
    camera.onvifEndpoint = columnText(statement, 8);
    camera.mainStreamUri = columnText(statement, 9);
    camera.subStreamUri = columnText(statement, 10);
    camera.ptzSupported = sqlite3_column_int(statement, 11) != 0;
    camera.enabled = sqlite3_column_int(statement, 12) != 0;
    camera.status = parseStatus(sqlite3_column_int(statement, 13));

    sqlite3_finalize(statement);
    return Result<CameraDescriptor>::success(std::move(camera));
}

Result<void> SqliteCameraRepository::upsert(const CameraDescriptor& camera) {
    if (camera.id.value.empty()) {
        return Result<void>::failure("Camera id is required");
    }

    std::lock_guard lock(mutex_);
    if (db_ == nullptr) {
        return Result<void>::failure("Database is not available");
    }
    if (sqlite3_db_readonly(db_, "main") == 1) {
        return Result<void>::failure("Database opened in readonly mode: " + databasePath_);
    }

    sqlite3_stmt* statement = nullptr;
    const char* sql =
        "INSERT INTO cameras("
        "id,name,host,port,username,password,manufacturer,model,onvif_endpoint,"
        "main_stream_uri,sub_stream_uri,ptz_supported,enabled,status"
        ") VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14)"
        "ON CONFLICT(id) DO UPDATE SET "
        "name=excluded.name,host=excluded.host,port=excluded.port,username=excluded.username,"
        "password=excluded.password,manufacturer=excluded.manufacturer,model=excluded.model,"
        "onvif_endpoint=excluded.onvif_endpoint,main_stream_uri=excluded.main_stream_uri,"
        "sub_stream_uri=excluded.sub_stream_uri,ptz_supported=excluded.ptz_supported,"
        "enabled=excluded.enabled,status=excluded.status;";

    if (sqlite3_prepare_v2(db_, sql, -1, &statement, nullptr) != SQLITE_OK) {
        return Result<void>::failure("Failed to prepare upsert query");
    }

    sqlite3_bind_text(statement, 1, camera.id.value.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(statement, 2, camera.name.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(statement, 3, camera.host.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(statement, 4, camera.port);
    sqlite3_bind_text(statement, 5, camera.username.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(statement, 6, camera.password.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(statement, 7, camera.manufacturer.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(statement, 8, camera.model.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(statement, 9, camera.onvifEndpoint.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(statement, 10, camera.mainStreamUri.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(statement, 11, camera.subStreamUri.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(statement, 12, camera.ptzSupported ? 1 : 0);
    sqlite3_bind_int(statement, 13, camera.enabled ? 1 : 0);
    sqlite3_bind_int(statement, 14, toStatusInt(camera.status));

    if (sqlite3_step(statement) != SQLITE_DONE) {
        const auto message = std::string(sqlite3_errmsg(db_));
        sqlite3_finalize(statement);
        return Result<void>::failure("Failed to upsert camera: " + message);
    }

    sqlite3_finalize(statement);
    return Result<void>::success();
}

Result<void> SqliteCameraRepository::remove(const CameraId& id) {
    std::lock_guard lock(mutex_);
    if (db_ == nullptr) {
        return Result<void>::failure("Database is not available");
    }

    sqlite3_stmt* statement = nullptr;
    if (sqlite3_prepare_v2(db_, "DELETE FROM cameras WHERE id=?1;", -1, &statement, nullptr)
        != SQLITE_OK) {
        return Result<void>::failure("Failed to prepare remove query");
    }
    sqlite3_bind_text(statement, 1, id.value.c_str(), -1, SQLITE_TRANSIENT);
    if (sqlite3_step(statement) != SQLITE_DONE) {
        const auto message = std::string(sqlite3_errmsg(db_));
        sqlite3_finalize(statement);
        return Result<void>::failure("Failed to remove camera: " + message);
    }
    const auto rows = sqlite3_changes(db_);
    sqlite3_finalize(statement);
    if (rows == 0) {
        return Result<void>::failure("Camera not found: " + id.value);
    }
    return Result<void>::success();
}

}  // namespace vms
