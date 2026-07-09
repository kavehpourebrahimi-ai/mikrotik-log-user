#include "vms/common/Config.hpp"

#include <fstream>
#include <sstream>

namespace vms {

Config Config::fromFile(const std::string& path) {
    Config config;
    std::ifstream input(path);
    if (!input.is_open()) {
        return config;
    }

    std::string line;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') {
            continue;
        }

        const auto pos = line.find('=');
        if (pos == std::string::npos) {
            continue;
        }

        auto key = line.substr(0, pos);
        auto value = line.substr(pos + 1);
        config.set(key, value);
    }

    return config;
}

std::string Config::get(std::string_view key, std::string_view defaultValue) const {
    const auto it = values_.find(std::string(key));
    if (it == values_.end()) {
        return std::string(defaultValue);
    }
    return it->second;
}

void Config::set(std::string_view key, std::string_view value) {
    values_[std::string(key)] = std::string(value);
}

bool Config::contains(std::string_view key) const {
    return values_.contains(std::string(key));
}

}  // namespace vms
