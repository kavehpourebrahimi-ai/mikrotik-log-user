#pragma once

#include <memory>
#include <mutex>
#include <string>
#include <typeindex>
#include <unordered_map>

namespace vms {

/// @brief Lightweight service locator for dependency injection.
class ServiceRegistry {
public:
    template <typename T>
    void registerService(std::shared_ptr<T> service) {
        std::lock_guard lock(mutex_);
        services_[std::type_index(typeid(T))] = std::move(service);
    }

    template <typename T>
    [[nodiscard]] std::shared_ptr<T> resolve() const {
        std::lock_guard lock(mutex_);
        const auto it = services_.find(std::type_index(typeid(T)));
        if (it == services_.end()) {
            return nullptr;
        }
        return std::static_pointer_cast<T>(it->second);
    }

    template <typename T>
    [[nodiscard]] bool has() const {
        std::lock_guard lock(mutex_);
        return services_.contains(std::type_index(typeid(T)));
    }

private:
    mutable std::mutex mutex_;
    std::unordered_map<std::type_index, std::shared_ptr<void>> services_;
};

}  // namespace vms
