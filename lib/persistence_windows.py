import os
import subprocess
import sys


def is_persistent(service_name: str) -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run"
        )
        winreg.QueryValueEx(key, service_name)
        return True
    except Exception:
        return False


def install_persistence(service_name: str, exe_path: str):
    exec_start = (
        f'{sys.executable} "{exe_path}"'
        if exe_path.endswith('.py')
        else f'"{exe_path}"'
    )
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, service_name, 0, winreg.REG_SZ, exec_start)
        key.Close()
    except Exception:
        pass


def remove_persistence(service_name: str):
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, service_name)
        key.Close()
    except Exception:
        pass
