# Enterprise VMS — Phase 1 Architecture

## Mission

Design and implement a commercial-grade, vendor-neutral Video Management System (VMS/NVR) with a headless Windows Server, Windows Client, REST API, WebSocket Gateway, Plugin SDK, and future Mobile SDK.

Phase 1 delivers the **modular architecture foundation**: shared interfaces, domain models, independent buildable modules, unit tests, and server bootstrap — without a monolithic codebase.

## System Context

```mermaid
flowchart TB
    subgraph Clients
        WinClient[Windows Client - Qt Phase 4]
        Mobile[Mobile SDK - Future]
        Integrations[Third-party Integrations]
    end

    subgraph Gateway
        REST[REST API /api/v1]
        WS[WebSocket Gateway]
    end

    subgraph Server["VMS Server (Headless Windows Service)"]
        Core[Vms.Core Interfaces]
        Camera[Camera Manager]
        Onvif[ONVIF Discovery]
        Stream[RTSP Pipeline]
        Record[Recording Engine]
        Play[Playback Engine]
        Storage[Storage Manager]
        Auth[Auth / RBAC]
        Events[Event / Alarm Engine]
        Plugins[Plugin Host]
    end

    subgraph StorageBackends
        Local[Local Disk]
        RAID[RAID]
        ISCSI[iSCSI]
        NAS[NAS]
    end

  Cameras[(IP Cameras 256-1024+)]

    Cameras -->|RTSP/RTP H.264/H.265| Stream
    Onvif -->|WS-Discovery| Cameras
    WinClient --> REST
    WinClient --> WS
    Integrations --> REST
    Mobile --> REST
    REST --> Server
    WS --> Events
    Record --> Storage
    Play --> Storage
    Storage --> Local
    Storage --> RAID
    Storage --> ISCSI
    Storage --> NAS
    Plugins --> Events
```

## Module Dependency Graph

```mermaid
flowchart LR
    Core[Vms.Core]
    Common[Vms.Common]
    Storage[Vms.Storage]
    Camera[Vms.Camera]
    Auth[Vms.Auth]
    Events[Vms.Events]
    Streaming[Vms.Streaming]
    Recording[Vms.Recording]
    Playback[Vms.Playback]
    Onvif[Vms.Onvif]
    Api[Vms.Api]
    Plugin[Vms.PluginSdk]
    Server[Vms.Server]

    Common --> Core
    Storage --> Common
    Camera --> Storage
    Auth --> Common
    Events --> Common
    Streaming --> Common
    Recording --> Streaming
    Recording --> Storage
    Playback --> Storage
    Onvif --> Common
    Api --> Core
    Plugin --> Events
    Server --> Camera
    Server --> Auth
    Server --> Events
    Server --> Streaming
    Server --> Recording
    Server --> Playback
    Server --> Onvif
    Server --> Plugin
```

## Core Design Principles

| Principle | Implementation |
|-----------|----------------|
| No monolith | 13 independent CMake modules under `modules/` |
| SOLID | Pure virtual interfaces in `Vms.Core`; concrete modules depend on abstractions |
| Thread-safe | `std::mutex` on shared mutable state; async I/O planned for Phase 2 |
| Pass-through recording | `IRecordingWriter` contract writes original main-stream bitstream |
| Substream live view | `StreamProfile::Sub` for grids; `StreamProfile::Main` on maximize |
| DI | `ServiceRegistry` wires implementations in `ServerHost` |
| Testability | Catch2 unit tests per module |

## Interface Layer (`Vms.Core`)

All subsystems communicate through documented interfaces:

- **Camera**: `ICameraRepository`, `ICameraManager`
- **Discovery**: `IOnvifDiscovery`
- **Streaming**: `IStreamPipeline`, `IStreamSession`
- **Recording**: `IRecordingEngine`, `IRecordingWriter`
- **Playback**: `IPlaybackEngine`
- **Storage**: `IStorageProvider`, `IStorageManager`
- **Security**: `IAuthenticationService`, `IAuthorizationService`
- **Events**: `IEventBus`, `IEventEngine`
- **Plugins**: `IPlugin`, `IPluginHost`

## Recording & Live View Strategy

```mermaid
sequenceDiagram
    participant Cam as IP Camera
    participant Pipe as StreamPipeline
    participant Rec as RecordingEngine
    participant Store as StorageManager
    participant Client as Windows Client

    Cam->>Pipe: Main stream (H.264/H.265)
    Pipe->>Rec: Encoded frames (no transcode)
    Rec->>Store: Segment files (.vms)
    Cam->>Pipe: Sub stream
    Pipe->>Client: Grid tiles (substream)
    Client->>Pipe: Tile maximized
    Pipe->>Client: Switch to main stream
```

## Database Schema (Phase 2)

Relational schema will be introduced with SQLite/PostgreSQL in Phase 2. Planned tables:

- `cameras`, `camera_streams`, `recording_segments`, `bookmarks`
- `users`, `roles`, `role_permissions`, `audit_log`
- `events`, `alarms`, `storage_volumes`, `retention_policies`

Phase 1 uses `InMemoryCameraRepository` and filesystem-backed segments.

## Technology Stack

| Layer | Phase 1 | Future Phases |
|-------|---------|---------------|
| Core interfaces | C++20 | C++20 |
| Server host | C++20 (Linux dev / Windows deploy) | Windows Service wrapper |
| RTSP/ONVIF | Interface stubs | Boost.Asio + gSOAP/ONVIF |
| REST/WebSocket | API contracts | Boost.Beast or .NET 8 gateway |
| Client | N/A | Qt 6 (Windows) |
| AI modules | Plugin SDK interface | ONNX Runtime plugins |

## Phase Roadmap

| Phase | Scope |
|-------|-------|
| **1 (current)** | Architecture, interfaces, module skeleton, tests, server bootstrap |
| **2** | RTSP ingest, ONVIF discovery, REST/WebSocket gateway, DB persistence |
| **3** | Recording index, playback demux, retention enforcement |
| **4** | Qt Windows client, live grid, timeline, PTZ |
| **5** | Windows Service installer, TLS, audit, AI plugin samples |

## Class Diagram (Core Abstractions)

```mermaid
classDiagram
    class ICameraManager {
        +getStreamInfo()
        +setEnabled()
        +reconnect()
    }
    class IStreamPipeline {
        +acquire()
        +release()
    }
    class IRecordingEngine {
        +startRecording()
        +stopRecording()
    }
    class IStorageManager {
        +registerProvider()
        +listVolumes()
        +enforceRetention()
    }
    class IAuthenticationService {
        +authenticate()
        +validateToken()
    }
    class IEventBus {
        +publish()
        +subscribe()
    }

    ICameraManager --> ICameraRepository
    IRecordingEngine --> IStreamPipeline
    IRecordingEngine --> IStorageManager
    IEventEngine --> IEventBus
```

## Security Model

- **Authentication**: Token-based sessions (`IAuthenticationService`)
- **Authorization**: RBAC with granular `Permission` enum
- **Default admin**: `admin` / `admin` (change in production)
- **Phase 2**: TLS 1.3, encrypted credential storage, audit trail

## Performance Targets

- 256 cameras initial capacity; architecture supports 1024+
- Main-stream recording without transcoding minimizes CPU
- Substream fan-out for multi-client live grids
- 24/7 uptime: graceful reconnect, health events, storage monitoring
