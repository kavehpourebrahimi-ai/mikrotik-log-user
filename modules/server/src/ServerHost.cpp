#include "vms/server/ServerHost.hpp"

#include "vms/auth/AuthenticationService.hpp"
#include "vms/auth/AuthorizationService.hpp"
#include "vms/camera/CameraManager.hpp"
#include "vms/common/Config.hpp"
#include "vms/common/Logging.hpp"
#include "vms/events/EventBus.hpp"
#include "vms/events/EventEngine.hpp"
#include "vms/onvif/OnvifDiscovery.hpp"
#include "vms/playback/PlaybackEngine.hpp"
#include "vms/plugin/PluginHost.hpp"
#include "vms/recording/RecordingEngine.hpp"
#include "vms/storage/LocalStorageProvider.hpp"
#include "vms/storage/FileCameraRepository.hpp"
#include "vms/storage/SqliteCameraRepository.hpp"
#include "vms/storage/StorageManager.hpp"
#include "vms/streaming/StreamPipeline.hpp"
#include "vms/server/HttpApiServer.hpp"

#include <string>
#include <filesystem>

namespace vms {

ServerHost::ServerHost() {
    auto config = Config::fromFile("vms-server.conf");
    if (config.contains("log.level")) {
        logger().log(LogLevel::Info, "ServerHost", "Loaded server configuration");
    }

    const auto storageRoot = config.get("storage.root", "./vms-data");
    std::filesystem::create_directories(storageRoot);
    std::shared_ptr<ICameraRepository> repository;
#if defined(VMS_HAS_SQLITE3)
    const auto dbPath = config.get("db.path", storageRoot + "/vms.db");
    repository = std::make_shared<SqliteCameraRepository>(dbPath);
#else
    const auto dbPath = config.get("db.path", storageRoot + "/cameras.json");
    repository = std::make_shared<FileCameraRepository>(dbPath);
#endif
    auto storageManager = std::make_shared<StorageManager>();
    auto streamPipeline = std::make_shared<StreamPipeline>();
    auto eventBus = std::make_shared<EventBus>();
    auto onvifDiscovery = std::make_shared<OnvifDiscovery>();

    try {
        apiPort_ = std::stoi(config.get("api.port", "8080"));
    } catch (...) {
        apiPort_ = 8080;
    }
    auto localProvider = std::make_shared<LocalStorageProvider>(storageRoot);
    storageManager->registerProvider("local-primary", localProvider);

    registry_.registerService<ICameraRepository>(repository);
    registry_.registerService<ICameraManager>(std::make_shared<CameraManager>(repository));
    registry_.registerService<IStorageManager>(storageManager);
    registry_.registerService<IStreamPipeline>(streamPipeline);
    registry_.registerService<IRecordingEngine>(
        std::make_shared<RecordingEngine>(storageManager, streamPipeline));
    registry_.registerService<IPlaybackEngine>(std::make_shared<PlaybackEngine>());
    registry_.registerService<IAuthenticationService>(std::make_shared<AuthenticationService>());
    registry_.registerService<IAuthorizationService>(std::make_shared<AuthorizationService>());
    registry_.registerService<IEventBus>(eventBus);
    registry_.registerService<IEventEngine>(std::make_shared<EventEngine>(*eventBus));
    registry_.registerService<IOnvifDiscovery>(onvifDiscovery);
    registry_.registerService<IPluginHost>(std::make_shared<PluginHost>(*eventBus));
}

ServerHost::~ServerHost() {
    stop();
}

void ServerHost::start() {
    if (running_) {
        return;
    }

    auto cameraRepository = registry_.resolve<ICameraRepository>();
    auto recordingEngine = registry_.resolve<IRecordingEngine>();
    auto storageManager = registry_.resolve<IStorageManager>();
    auto authenticationService = registry_.resolve<IAuthenticationService>();
    auto onvifDiscovery = registry_.resolve<IOnvifDiscovery>();

    if (!cameraRepository || !recordingEngine || !storageManager || !authenticationService || !onvifDiscovery) {
        logger().log(LogLevel::Error, "ServerHost", "Failed to resolve core services");
        return;
    }

    auto config = Config::fromFile("vms-server.conf");
    const auto storageRoot = config.get("storage.root", "./vms-data");
    const auto auditLog = std::filesystem::path(storageRoot) / "audit.log";

    apiServer_ = std::make_unique<HttpApiServer>(
        std::move(cameraRepository),
        std::move(recordingEngine),
        std::move(storageManager),
        std::move(authenticationService),
        std::move(onvifDiscovery),
        auditLog,
        apiPort_);
    const auto apiStartResult = apiServer_->start();
    if (!apiStartResult.ok()) {
        logger().log(LogLevel::Error, "ServerHost", "Failed to start HTTP API: " + apiStartResult.error);
        return;
    }

    running_ = true;
    logger().log(LogLevel::Info, "ServerHost", "Enterprise VMS server started");
    logger().log(
        LogLevel::Info,
        "ServerHost",
        "API endpoints available at http://127.0.0.1:" + std::to_string(apiPort_) + "/api/v1");
}

void ServerHost::stop() {
    if (!running_) {
        return;
    }

    running_ = false;
    if (apiServer_) {
        apiServer_->stop();
    }
    logger().log(LogLevel::Info, "ServerHost", "Enterprise VMS server stopped");
}

}  // namespace vms
