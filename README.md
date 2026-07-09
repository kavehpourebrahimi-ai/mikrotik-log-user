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
./build/modules/client/vms_client --server http://127.0.0.1:8080
```

### Use the server API (real functionality)

```bash
# Health
curl http://127.0.0.1:8080/api/v1/health

# Login (default bootstrap account)
TOKEN=$(curl -s -X POST http://127.0.0.1:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.access_token')

# Add camera
curl -X POST http://127.0.0.1:8080/api/v1/cameras \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Lobby","host":"192.168.1.10","mainStreamUri":"rtsp://192.168.1.10/main"}'

# List cameras
curl http://127.0.0.1:8080/api/v1/cameras -H "Authorization: Bearer $TOKEN"
```

### Interactive client menu (SmartPSS-style operational flow)

`vms_client` now provides an operator menu with:
- Login
- Health dashboard
- Camera list/add/remove
- Start/stop recording
- Recording status
- Storage volume status

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
  client/        Client executable bootstrap
```

## Download Windows .exe files

The workflow `.github/workflows/windows-artifacts.yml` produces downloadable
Windows binaries on each push/PR:

- `vms_server.exe`
- `vms_client.exe`
- `EnterpriseVmsSetup.exe` (Windows installer)
- runtime DLL files and startup scripts

In GitHub:
1. Open **Actions**.
2. Select **Windows Artifacts** run.
3. Download artifact **enterprise-vms-windows-executables**.
4. Run `EnterpriseVmsSetup.exe` for installation.

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
