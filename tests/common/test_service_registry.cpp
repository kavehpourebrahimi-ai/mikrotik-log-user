#include <catch2/catch_test_macros.hpp>

#include "vms/common/ServiceRegistry.hpp"
#include "vms/core/Interfaces.hpp"

namespace {

class DummyRepository final : public vms::ICameraRepository {
public:
    [[nodiscard]] std::vector<vms::CameraDescriptor> list() const override {
        return {};
    }

    [[nodiscard]] vms::Result<vms::CameraDescriptor> get(
        const vms::CameraId&) const override {
        return vms::Result<vms::CameraDescriptor>::failure("not implemented");
    }

    vms::Result<void> upsert(const vms::CameraDescriptor&) override {
        return vms::Result<void>::success();
    }

    vms::Result<void> remove(const vms::CameraId&) override {
        return vms::Result<void>::success();
    }
};

}  // namespace

TEST_CASE("ServiceRegistry resolves registered services", "[common]") {
    vms::ServiceRegistry registry;
    auto repository = std::make_shared<DummyRepository>();
    registry.registerService<vms::ICameraRepository>(repository);

    REQUIRE(registry.has<vms::ICameraRepository>());
    REQUIRE(registry.resolve<vms::ICameraRepository>() == repository);
}
