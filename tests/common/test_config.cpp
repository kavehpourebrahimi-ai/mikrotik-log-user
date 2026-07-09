#include <catch2/catch_test_macros.hpp>

#include <filesystem>
#include <fstream>

#include "vms/common/Config.hpp"

TEST_CASE("Config parses key value pairs", "[common]") {
    const auto path = std::filesystem::temp_directory_path() / "vms-test.conf";
    {
        std::ofstream out(path);
        out << "storage.root=/data/vms\n";
        out << "# comment\n";
        out << "log.level=info\n";
    }

    const auto config = vms::Config::fromFile(path.string());
    REQUIRE(config.get("storage.root") == "/data/vms");
    REQUIRE(config.get("log.level") == "info");
    REQUIRE(config.get("missing", "default") == "default");

    std::filesystem::remove(path);
}
