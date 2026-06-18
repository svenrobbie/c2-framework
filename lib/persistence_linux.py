import os
import subprocess
import sys


def is_persistent(service_name: str) -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", f"{service_name}.service"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() == "enabled"
    except Exception:
        return False


def install_persistence(service_name: str, exe_path: str):
    exec_start = (
        f'{sys.executable} "{exe_path}"'
        if exe_path.endswith('.py')
        else f'"{exe_path}"'
    )
    service_dir = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(service_dir, exist_ok=True)
    service_path = os.path.join(service_dir, f"{service_name}.service")
    with open(service_path, "w") as f:
        f.write(f"""[Unit]
Description=Hardware Helper ({service_name})

[Service]
ExecStart={exec_start}
Restart=on-failure
RestartSec=60

[Install]
WantedBy=default.target
""")
    subprocess.run(["systemctl", "--user", "daemon-reload"],
                   capture_output=True, timeout=10)
    subprocess.run(["systemctl", "--user", "enable", f"{service_name}.service"],
                   capture_output=True, timeout=10)
    subprocess.run(["systemctl", "--user", "start", f"{service_name}.service"],
                   capture_output=True, timeout=10)


def remove_persistence(service_name: str):
    try:
        subprocess.run(
            ["systemctl", "--user", "stop", f"{service_name}.service"],
            capture_output=True, timeout=10
        )
        subprocess.run(
            ["systemctl", "--user", "disable", f"{service_name}.service"],
            capture_output=True, timeout=10
        )
        service_path = os.path.expanduser(
            f"~/.config/systemd/user/{service_name}.service"
        )
        if os.path.exists(service_path):
            os.remove(service_path)
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True, timeout=10
        )
    except Exception:
        pass
