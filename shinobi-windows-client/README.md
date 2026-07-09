# Shinobi Operator Desk

Lightweight **Windows client** for security guards and control-room operators connecting to a remote **Shinobi** server.

## Design goal

- **Server on Linux** handles recording, storage, and camera ingest.
- **Client on weak Windows PCs** handles monitoring, playback, and event response.
- No expensive Shinobi Go license required for basic operator workflows.

## Performance modes

| Mode | Best for | Behavior |
| --- | --- | --- |
| **Eco** | Weak PCs, old hardware | Snapshot refresh in grid, live video only in focus panel |
| **Balanced** | Normal workstations | Selected tile streams live, others use snapshots |
| **Performance** | Strong PCs | Live HLS on all visible tiles |

Default is **Eco** so the client stays responsive even on low-end operator machines.

## Current features (v0.2.0)

- Operator login to Shinobi server
- Camera search and paginated live grid
- Focus panel for one full live stream
- Snapshot-based grid mode for weak systems
- Recording list and playback for selected camera
- Live event feed via Socket.io
- Saved server profiles
- Lazy-loaded HLS decoder (smaller startup bundle)

## Run locally

```bash
cd shinobi-windows-client
npm install
npm run dev
```

Windows desktop shell:

```bash
npm run tauri dev
npm run tauri build
```

## Recommended deployment

```
[256 IP Cameras] -> [Linux Shinobi Server] <-VPN/LAN-> [Windows Operator PCs]
```

Use **Eco** mode on weak operator PCs. Use **Balanced** or **Performance** only on stronger control-room workstations.

## Next steps

- User and permission management
- PTZ controls in focus panel
- Alarm acknowledgement workflow
- Multi-server switching
- Hardware video decode on Windows
- Branded MSI installer
