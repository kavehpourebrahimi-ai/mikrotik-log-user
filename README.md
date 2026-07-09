# Enterprise Video Management System (VMS/NVR)

Commercial-grade, vendor-neutral Video Management System — modular C++20 architecture for 256–1024+ IP cameras.

## Status: Phase 1 — Architecture Foundation

This repository implements the foundational module structure defined in the [Master Specification](docs/architecture.md):

- **13 independent modules** (not a monolith)
- **Documented C++ interfaces** for all major subsystems
- **Unit tests** with Catch2
- **Headless server bootstrap** with dependency injection
- **Architecture diagrams** and build instructions

## Quick Start

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DVMS_BUILD_TESTS=ON
cmake --build build --parallel
ctest --test-dir build --output-on-failure
./build/modules/server/vms_server
```

See [docs/BUILD.md](docs/BUILD.md) for full build instructions and [docs/architecture.md](docs/architecture.md) for system design.

## Module Layout

```
modules/
  core/          Shared types and abstract interfaces
  common/        Logging, configuration, service registry
  storage/       Storage abstraction and camera repository
  camera/        Camera lifecycle management
  auth/          Authentication and RBAC
  events/        Event bus and alarm engine
  streaming/     RTSP pipeline (Phase 2)
  recording/     Pass-through recording engine
  playback/      Timeline playback engine
  onvif/         ONVIF discovery (Phase 2)
  api/           REST and WebSocket API contracts
  plugin-sdk/    Plugin host
  server/        Headless server executable
```

## Mandatory Requirements (Roadmap)

| Requirement | Phase |
|-------------|-------|
| 256+ camera architecture | 1 ✓ (interfaces) |
| ONVIF auto-discovery | 2 |
| RTSP H.264/H.265 ingest | 2 |
| Main-stream recording (no transcode) | 2–3 |
| Substream live grids | 4 (client) |
| REST API + WebSocket | 2 |
| Storage abstraction | 1 ✓ (local provider) |
| RBAC + auditing | 1 ✓ (RBAC), 2 (audit) |
| AI plugin modules | 5 |

## License

Proprietary — Enterprise VMS Project
