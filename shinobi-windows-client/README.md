# Shinobi Client

Windows desktop client for a remote **Shinobi** VMS server.

## Why this project

- Keep **Shinobi on Linux** for recording, ONVIF ingest, and storage at scale.
- Give operators a **native Windows workstation app** for live view and control.
- Optimize for large deployments by decoding only visible camera tiles.

## Recommended stack

| Layer | Choice |
| --- | --- |
| Server | [Shinobi on GitLab](https://gitlab.com/Shinobi-Systems/Shinobi) |
| Client shell | Tauri 2 + React + TypeScript |
| Live video | HLS via `hls.js` (phase 1), FLV/WebRTC later |
| Realtime events | Socket.io (`f: init`) |
| State | Zustand |

Do **not** use lightNVR as the backend for 256-camera enterprise deployments. It is optimized for edge/home use, not large VMS workloads.

## Current features

- Connect to a Shinobi server with email/password
- Load monitor list from `/monitor/{groupKey}`
- Live grid with pagination (64 cameras per page)
- Lazy stream activation with intersection observer
- Socket.io connection for server events
- Saved server profiles

## Planned features

- Recording browser and timeline playback
- Sub-account and permission management
- PTZ and alarm panels
- Multi-server switching
- Hardware-accelerated decoding on Windows
- MSI installer and auto-update

## Development

```bash
cd shinobi-windows-client
npm install
npm run dev
```

For the desktop shell on Windows:

```bash
npm run tauri dev
npm run tauri build
```

## Shinobi API references used

- Login: `POST /?json=true`
- Monitors: `GET /{auth}/monitor/{ke}`
- Live HLS: `GET /{auth}/hls/{ke}/{mid}/s.m3u8`
- Videos: `GET /{auth}/videos/{ke}/{mid}`
- Socket.io init: emit `{ f: "init", ke, auth, uid }`

## Build target

Primary target is **Windows 10/11 x64**. The same UI can also be built for Linux/macOS with Tauri if needed.
