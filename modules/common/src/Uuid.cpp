#include "vms/common/Uuid.hpp"

#include <iomanip>
#include <random>
#include <sstream>

namespace vms {

std::string generateUuid() {
    static thread_local std::mt19937_64 rng{std::random_device{}()};
    std::uniform_int_distribution<std::uint32_t> dist;

    const auto a = dist(rng);
    const auto b = dist(rng);
    const auto c = dist(rng);
    const auto d = dist(rng);

    std::ostringstream stream;
    stream << std::hex << std::setfill('0')
           << std::setw(8) << a << '-'
           << std::setw(4) << ((b >> 16) & 0xFFFF) << '-'
           << std::setw(4) << ((b & 0x0FFF) | 0x4000) << '-'
           << std::setw(4) << (((c >> 16) & 0x3FFF) | 0x8000) << '-'
           << std::setw(4) << (c & 0xFFFF)
           << std::setw(8) << d;

    return stream.str();
}

}  // namespace vms
