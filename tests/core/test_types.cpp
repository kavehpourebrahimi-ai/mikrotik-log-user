#include <catch2/catch_test_macros.hpp>

#include "vms/core/All.hpp"

TEST_CASE("CameraId comparison", "[core]") {
    vms::CameraId a{"camera-1"};
    vms::CameraId b{"camera-2"};
    REQUIRE(a < b);
    REQUIRE(a == vms::CameraId{"camera-1"});
}

TEST_CASE("Result success and failure", "[core]") {
    const auto ok = vms::Result<int>::success(42);
    REQUIRE(ok.ok());
    REQUIRE(*ok.value == 42);

    const auto err = vms::Result<int>::failure("boom");
    REQUIRE_FALSE(err.ok());
    REQUIRE(err.error == "boom");
}
