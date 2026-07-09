#pragma once

#include <mutex>
#include <string>
#include <vector>

#include "vms/core/Interfaces.hpp"

struct sqlite3;

namespace vms {

/// @brief SQLite-backed camera repository for persistent server state.
class SqliteCameraRepository final : public ICameraRepository {
public:
    explicit SqliteCameraRepository(std::string databasePath);
    ~SqliteCameraRepository() override;

    [[nodiscard]] std::vector<CameraDescriptor> list() const override;
    [[nodiscard]] Result<CameraDescriptor> get(const CameraId& id) const override;
    Result<void> upsert(const CameraDescriptor& camera) override;
    Result<void> remove(const CameraId& id) override;

private:
    Result<void> initializeSchema();
    [[nodiscard]] Result<void> open();
    void close();

    std::string databasePath_;
    mutable std::mutex mutex_;
    sqlite3* db_{nullptr};
};

}  // namespace vms
