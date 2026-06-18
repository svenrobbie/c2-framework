import React from 'react';
import { Monitor, ShieldAlert, Cpu, Laptop, Router, Radio, HelpCircle } from 'lucide-react';
import { Victim } from '../types';

interface VictimItemProps {
  victim: Victim;
  isSelected: boolean;
  onSelect: () => void;
}

export const VictimItem: React.FC<VictimItemProps> = ({ victim, isSelected, onSelect }) => {
  const getIcon = (type: string) => {
    switch (type) {
      case 'ransomware':
        return <ShieldAlert className="h-4.5 w-4.5" />;
      case 'botnet':
        return <Router className="h-4.5 w-4.5" />;
      case 'industrial':
        return <Radio className="h-4.5 w-4.5" />;
      case 'stager':
        return <Cpu className="h-4.5 w-4.5" />;
      case 'spyware':
        return <Laptop className="h-4.5 w-4.5" />;
      default:
        return <Monitor className="h-4.5 w-4.5" />;
    }
  };

  const getStatusBadge = (status: Victim['status']) => {
    switch (status) {
      case 'ONLINE':
        return (
          <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-[10px] font-bold border border-emerald-500/20 flex items-center gap-1">
            <span className="h-1.5 w-1.5 bg-emerald-400 rounded-full online-pulse"></span>
            ONLINE
          </span>
        );
      case 'ENCRYPTED':
        return (
          <span className="px-2 py-0.5 bg-rose-500/10 text-rose-400 rounded text-[10px] font-bold border border-rose-500/20">
            ENCRYPTED
          </span>
        );
      case 'WATCHDOG':
        return (
          <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded text-[10px] font-bold border border-amber-500/20">
            WATCHDOG
          </span>
        );
      case 'OFFLINE':
        return (
          <span className="px-2 py-0.5 bg-slate-800 text-slate-400 rounded text-[10px] font-bold border border-slate-700">
            OFFLINE
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 bg-slate-500/10 text-slate-400 rounded text-[10px] ">
            UNKNOWN
          </span>
        );
    }
  };

  return (
    <div
      onClick={onSelect}
      className={`group transition-all duration-200 cursor-pointer p-4 rounded-xl border flex items-center justify-between gap-3 ${
        isSelected
          ? 'bg-slate-900 border-primary/90 shadow-cyan-900/30 shadow'
          : 'bg-slate-950/40 border-slate-900 hover:border-slate-800 hover:bg-slate-900/40'
      }`}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div
          className={`p-2 rounded-lg transition-colors duration-200 shrink-0 ${
            isSelected
              ? 'bg-primary/20 text-primary'
              : 'bg-slate-900 text-slate-400 group-hover:bg-primary/10 group-hover:text-primary'
          }`}
        >
          {getIcon(victim.type)}
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <h3 className={`font-mono text-xs font-bold leading-none truncate ${
              isSelected ? 'text-primary' : 'text-slate-200'
            }`}>
              {victim.hostname}
            </h3>
            {victim.country !== '──' && (
              <span className="text-[9px] text-slate-500 px-1 bg-slate-900/60 rounded font-mono">
                {victim.country}
              </span>
            )}
          </div>
          <p className="text-[10px] text-slate-400 font-mono mt-1 break-all">
            {victim.os} | {victim.ip}
          </p>
        </div>
      </div>

      <div className="flex flex-col items-end gap-1.5 shrink-0">
        {getStatusBadge(victim.status)}
        <span className="text-[10px] text-slate-500 font-mono">{victim.lastSeen}</span>
      </div>
    </div>
  );
};
