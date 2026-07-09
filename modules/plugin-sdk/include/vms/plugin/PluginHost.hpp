#pragma once

#include <mutex>
#include <unordered_map>
#include <vector>

#include "vms/core/Interfaces.hpp"

namespace vms {

/// @brief In-process plugin host (Phase 4: dynamic module loading).
class PluginHost final : public IPluginHost {
public:
  explicit PluginHost(IEventBus& eventBus);

    Result<void> load(const std::string& modulePath) override;
    Result<void> unload(const std::string& pluginId) override;
    [[nodiscard]] std::vector<std::string> loadedPlugins() const override;

private:
    IEventBus& eventBus_;
    mutable std::mutex mutex_;
    std::unordered_map<std::string, std::shared_ptr<IPlugin>> plugins_;
};

}  // namespace vms
