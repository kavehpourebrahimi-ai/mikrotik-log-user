#pragma once

#include "vms/core/Interfaces.hpp"

#include <atomic>
#include <memory>
#include <thread>

namespace httplib {
class Server;
}

namespace vms {

/// @brief REST API host exposing core VMS operations.
class HttpApiServer {
public:
    HttpApiServer(
        std::shared_ptr<ICameraRepository> cameraRepository,
        std::shared_ptr<IRecordingEngine> recordingEngine,
        std::shared_ptr<IStorageManager> storageManager,
        std::shared_ptr<IAuthenticationService> authenticationService,
        int port);

    ~HttpApiServer();

    Result<void> start();
    void stop();
    [[nodiscard]] bool isRunning() const noexcept { return running_.load(); }

private:
    std::shared_ptr<ICameraRepository> cameraRepository_;
    std::shared_ptr<IRecordingEngine> recordingEngine_;
    std::shared_ptr<IStorageManager> storageManager_;
    std::shared_ptr<IAuthenticationService> authenticationService_;
    int port_{8080};
    std::atomic<bool> running_{false};
    std::unique_ptr<httplib::Server> server_;
    std::thread serverThread_;
};

}  // namespace vms
