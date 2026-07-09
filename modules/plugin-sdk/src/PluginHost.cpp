#include "vms/plugin/PluginHost.hpp"

namespace vms {

PluginHost::PluginHost(IEventBus& eventBus) : eventBus_(eventBus) {
    (void)eventBus_;
}

Result<void> PluginHost::load(const std::string& modulePath) {
    (void)modulePath;
    return Result<void>::failure("Dynamic plugin loading is not enabled in Phase 1");
}

Result<void> PluginHost::unload(const std::string& pluginId) {
    std::lock_guard lock(mutex_);
    if (!plugins_.erase(pluginId)) {
        return Result<void>::failure("Plugin not loaded: " + pluginId);
    }
    return Result<void>::success();
}

std::vector<std::string> PluginHost::loadedPlugins() const {
    std::lock_guard lock(mutex_);
    std::vector<std::string> ids;
    ids.reserve(plugins_.size());
    for (const auto& [id, _] : plugins_) {
        ids.push_back(id);
    }
    return ids;
}

}  // namespace vms
