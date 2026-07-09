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
#include "vms/storage/InMemoryCameraRepository.hpp"
#include "vms/storage/LocalStorageProvider.hpp"
#include "vms/storage/StorageManager.hpp"
#include "vms/streaming/StreamPipeline.hpp"

namespace vms {

ServerHost::ServerHost() {
    auto config = Config::fromFile("vms-server.conf");
    if (config.contains("log.level")) {
        logger().log(LogLevel::Info, "ServerHost", "Loaded server configuration");
    }

    auto repository = std::make_shared<InMemoryCameraRepository>();
    auto storageManager = std::make_shared<StorageManager>();
    auto streamPipeline = std::make_shared<StreamPipeline>();
    auto eventBus = std::make_shared<EventBus>();

    const auto storageRoot = config.get("storage.root", "./vms-data");
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
    registry_.registerService<IOnvifDiscovery>(std::make_shared<OnvifDiscovery>());
    registry_.registerService<IPluginHost>(std::make_shared<PluginHost>(*eventBus));
}

void ServerHost::start() {
    if (running_) {
        return;
    }

    running_ = true;
    logger().log(LogLevel::Info, "ServerHost", "Enterprise VMS server started");
}

void ServerHost::stop() {
    if (!running_) {
        return;
    }

    running_ = false;
    logger().log(LogLevel::Info, "ServerHost", "Enterprise VMS server stopped");
}

}  // namespace vms
