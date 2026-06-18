import React from 'react';
import { LogEntry } from '../types';

interface CommandLogProps {
  logs: LogEntry[];
  onClearLogs: () => void;
}

export const CommandLog: React.FC<CommandLogProps> = ({ logs, onClearLogs }) => {
  const getActionColor = (action: string) => {
    switch (action) {
      case 'encrypt':
        return 'border-rose-500 bg-rose-500/10 text-rose-400';
      case 'decrypt':
        return 'border-amber-500 bg-amber-500/10 text-amber-400';
      case 'persist':
        return 'border-purple-500 bg-purple-500/10 text-purple-400';
      case 'exec':
        return 'border-blue-500 bg-blue-500/10 text-blue-400';
      case 'status':
        return 'border-emerald-500 bg-emerald-500/10 text-emerald-400';
      case 'watchdog':
        return 'border-amber-600 bg-amber-600/10 text-amber-500';
      case 'destroy':
      case 'self_destruct':
        return 'border-red-600 bg-red-600/10 text-red-500';
      case 'screenshot':
        return 'border-sky-500 bg-sky-500/10 text-sky-400';
      case 'pslist':
        return 'border-violet-500 bg-violet-500/10 text-violet-400';
      case 'pskill':
        return 'border-orange-500 bg-orange-500/10 text-orange-400';
      case 'steal_browsers':
        return 'border-rose-500 bg-rose-500/10 text-rose-400';
      case 'scare':
        return 'border-cyan-400 bg-cyan-400/10 text-cyan-300';
      case 'network_info':
        return 'border-cyan-500 bg-cyan-500/10 text-cyan-400';
      case 'upload':
        return 'border-teal-500 bg-teal-500/10 text-teal-400';
      case 'download':
        return 'border-sky-500 bg-sky-500/10 text-sky-400';
      case 'show_ransomnote':
        return 'border-pink-500 bg-pink-500/10 text-pink-400';
      default:
        return 'border-slate-500 bg-slate-500/10 text-slate-400';
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-950/80 overflow-hidden terminal-glow border-b border-slate-900">
      <div className="px-5 py-3 flex items-center justify-between bg-slate-900/60 border-b border-slate-900">
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-cyan-400 online-pulse"></span>
          <h2 className="font-mono text-xs font-bold text-primary uppercase tracking-wider">
            DECRYPTED COMMAND TELEMETRY LOGS
          </h2>
        </div>
        <button
          onClick={onClearLogs}
          title="Flush local buffer logs"
          className="text-xs text-slate-500 hover:text-rose-400 font-mono transition-colors focus:outline-none flex items-center gap-1 cursor-pointer"
        >
          [ Flush Logs ]
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-5 flex flex-col gap-4 font-mono text-xs">
        {logs.length === 0 ? (
          <div className="text-slate-600 italic font-mono text-center my-auto">
            &lt; Log buffer flushed. Awaiting next telemetry cycle &gt;
          </div>
        ) : (
          logs.map((log) => {
            const colors = getActionColor(log.action);
            return (
              <div
                key={log.id}
                className={`border-l-2 p-3 bg-slate-900/25 rounded-r-lg transition-all border-slate-800 ${colors.split(' ')[0]}`}
              >
                <div className="flex items-center gap-2 text-[10px] text-slate-500 mb-1 flex-wrap">
                  <span>[{log.timestamp}]</span>
                  <span className="text-primary font-bold">{log.target}</span>
                  <span className={`px-1.5 py-0.2 rounded font-bold uppercase text-[9px] ${colors.split(' ').slice(1).join(' ')}`}>
                    {log.action}
                  </span>
                </div>
                <div className="text-slate-200 mt-1">$ {log.message}</div>
                {log.outputDetail && (
                  <div className="mt-2.5 pl-3 border-l border-slate-800 py-1 bg-slate-950/50 rounded p-2 text-slate-400 text-[11px] font-mono whitespace-pre overflow-x-auto custom-scrollbar leading-tight">
                    {log.outputDetail}
                  </div>
                )}
              </div>
            );
          })
        )}
        <div className="mt-auto pt-4 flex items-center gap-2 text-slate-600 italic text-[11px] font-mono">
          <span className="online-pulse text-cyan-400">_</span> Awaiting incoming beacons...
        </div>
      </div>
    </div>
  );
};
