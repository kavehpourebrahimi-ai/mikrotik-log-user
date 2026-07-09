# Build Instructions — Enterprise VMS Phase 1

## Prerequisites

### Linux (development)

- CMake 3.20+
- GCC 11+ or Clang 14+ with C++20 support
- Git

### Windows (target deployment)

- Visual Studio 2022 with C++ Desktop Development
- CMake 3.20+
- (Future) Qt 6.x, Boost 1.83+

## Build (Linux)

```bash
cd /workspace
cmake -B build -DCMAKE_BUILD_TYPE=Release -DVMS_BUILD_TESTS=ON
cmake --build build --parallel
```

## Run Tests

```bash
cd build
ctest --output-on-failure
# or
./vms_tests
```

## Run Server

```bash
./build/modules/server/vms_server
```

Optional configuration file `vms-server.conf` in the working directory:

```ini
storage.root=./vms-data
log.level=info
```

## Module Targets

| Target | Type | Description |
|--------|------|-------------|
| `Vms::Core` | INTERFACE | Domain types and abstract interfaces |
| `Vms::Common` | STATIC | Logging, config, DI registry, UUID |
| `Vms::Storage` | STATIC | Local storage provider, camera repository |
| `Vms::Camera` | STATIC | Camera manager |
| `Vms::Auth` | STATIC | Authentication and RBAC |
| `Vms::Events` | STATIC | Event bus and alarm engine |
| `Vms::Streaming` | STATIC | RTSP pipeline (Phase 2) |
| `Vms::Recording` | STATIC | Recording engine |
| `Vms::Playback` | STATIC | Playback engine |
| `Vms::Onvif` | STATIC | ONVIF discovery (Phase 2) |
| `Vms::Api` | INTERFACE | REST/WebSocket contracts |
| `Vms::PluginSdk` | STATIC | Plugin host |
| `vms_server` | EXECUTABLE | Headless server bootstrap |
| `vms_tests` | EXECUTABLE | Catch2 unit tests |

## Build (Windows)

```powershell
cmake -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release
.\build\modules\server\Release\vms_server.exe
```

## Install Layout (planned)

```
C:\Program Files\EnterpriseVms\
  server\vms_server.exe
  client\ (Phase 4)
  plugins\
  data\
  config\vms-server.conf
```

## CI

GitHub Actions workflow `.github/workflows/ci.yml` builds and tests on Ubuntu.
