import React from 'react';
import { RefreshCw, Play, ShieldAlert, ArrowDown, Activity, Ban, Trash2, Cpu, HardDrive, Eye, List, Skull, Download, Globe } from 'lucide-react';
import { Victim } from '../types';

interface VictimDetailProps {
  victim: Victim;
  onAction: (actionType: string) => void;
  isActionInProgress: boolean;
}

export const VictimDetail: React.FC<VictimDetailProps> = ({ victim, onAction, isActionInProgress }) => {
  const isOffline = victim.status === 'OFFLINE';

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ONLINE': return { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', dot: 'bg-emerald-400' };
      case 'ENCRYPTED': return { bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/20', dot: 'bg-rose-400' };
      case 'WATCHDOG': return { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20', dot: 'bg-amber-400' };
      default: return { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/20', dot: 'bg-slate-500' };
    }
  };

  const currentStatus = getStatusColor(victim.status);
  const showEncrypted = victim.files_encrypted !== undefined || victim.files_found !== undefined;

  return (
    <div className="bg-slate-900/60 border-2 border-primary/50 rounded-xl p-5 flex flex-col gap-4 relative shadow-lg">
      <div className="flex justify-between items-start flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary/10 rounded-lg border border-primary/20">
            <Activity className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="font-mono text-base font-bold text-primary tracking-tight">{victim.hostname}</h3>
            <p className="text-xs text-slate-400 font-mono tracking-tight">
              {victim.os} | <span className="text-primary/90">{victim.ip}</span>
            </p>
          </div>
        </div>
        <span className={`px-2.5 py-1 ${currentStatus.bg} ${currentStatus.text} rounded-lg text-xs font-mono font-bold border ${currentStatus.border} flex items-center gap-1.5`}>
          <span className={`h-2 w-2 ${currentStatus.dot} rounded-full online-pulse`}></span>
          {victim.status}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-slate-950/40 rounded-lg border border-slate-800/60 font-mono text-xs">
        <div className="flex flex-col gap-1.5">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">AGENT ID</span>
          <span className="text-slate-300 font-semibold text-[11px] truncate">{victim.agent}</span>
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">PAYLOAD TYPE</span>
          <span className="text-slate-300 font-semibold text-[11px] truncate">{victim.type}</span>
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">LAST BEACON</span>
          <span className="text-slate-300 font-semibold text-[11px] truncate">{victim.lastSeen}</span>
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">PERSISTENT STATUS</span>
          <span className={`font-semibold text-[11px] ${victim.persistent ? 'text-emerald-400' : 'text-slate-500'}`}>
            {victim.persistent ? 'ACTIVE / YES' : 'TRANSIENT / NO'}
          </span>
        </div>
      </div>

      {showEncrypted && (
        <div className="flex gap-3 font-mono text-xs">
          {victim.files_found !== undefined && (
            <div className="flex items-center gap-2 bg-slate-950/30 px-3 py-2 rounded border border-slate-800/40">
              <span className="text-slate-500">Files Found:</span>
              <span className="text-slate-300 font-bold">{victim.files_found}</span>
            </div>
          )}
          {victim.files_encrypted !== undefined && (
            <div className="flex items-center gap-2 bg-slate-950/30 px-3 py-2 rounded border border-slate-800/40">
              <span className="text-slate-500">Encrypted:</span>
              <span className="text-rose-400 font-bold">{victim.files_encrypted}</span>
            </div>
          )}
        </div>
      )}

      {/* Primary Operations */}
      <div className="flex flex-col gap-2 pt-2 border-t border-slate-800/60">
        <span className="font-mono text-[10px] text-slate-400 font-bold tracking-wider uppercase mb-1">
          TACTICAL OPERATIONS
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <ActionButton onClick={() => onAction('encrypt')} disabled={isActionInProgress || isOffline || victim.status === 'ENCRYPTED'}
            className="bg-rose-950/40 hover:bg-rose-900/40 text-rose-400 border-rose-500/30 disabled:opacity-40">
            <ShieldAlert className="h-3.5 w-3.5" /> Encrypt
          </ActionButton>
          <ActionButton onClick={() => onAction('decrypt')} disabled={isActionInProgress || isOffline || victim.status !== 'ENCRYPTED'}
            className="bg-amber-950/40 hover:bg-amber-900/40 text-amber-400 border-amber-500/30 disabled:opacity-40">
            <RefreshCw className="h-3.5 w-3.5" /> Decrypt
          </ActionButton>
          <ActionButton onClick={() => onAction('execute')} disabled={isActionInProgress || isOffline}
            className="bg-blue-950/40 hover:bg-blue-900/40 text-blue-400 border-blue-500/30">
            <Play className="h-3.5 w-3.5" /> Exec
          </ActionButton>
          <ActionButton onClick={() => onAction('terminal')} disabled={isActionInProgress || isOffline}
            className="bg-slate-800/80 hover:bg-slate-700/80 text-white border-slate-700">
            &gt;_ Terminal
          </ActionButton>
          <ActionButton onClick={() => onAction('persist')} disabled={isActionInProgress || isOffline}
            className="bg-slate-800/80 hover:bg-slate-700/80 text-white border-slate-700">
            + Persist
          </ActionButton>
          <ActionButton onClick={() => onAction('status')} disabled={isActionInProgress || isOffline}
            className="bg-emerald-950/40 hover:bg-emerald-900/40 text-emerald-400 border-emerald-500/30">
            Status
          </ActionButton>
          <ActionButton onClick={() => onAction('download')} disabled={isActionInProgress || isOffline}
            className="bg-sky-950/40 hover:bg-sky-900/40 text-sky-400 border-sky-500/30">
            <ArrowDown className="h-3.5 w-3.5" /> Download
          </ActionButton>
          <ActionButton onClick={() => onAction('upload')} disabled={isActionInProgress || isOffline}
            className="bg-teal-950/40 hover:bg-teal-900/40 text-teal-400 border-teal-500/30">
            <Download className="h-3.5 w-3.5" /> Upload
          </ActionButton>
          <ActionButton onClick={() => onAction('netinfo')} disabled={isActionInProgress || isOffline}
            className="bg-cyan-950/40 hover:bg-cyan-900/40 text-cyan-400 border-cyan-500/30">
            <Globe className="h-3.5 w-3.5" /> NetInfo
          </ActionButton>
          <ActionButton onClick={() => onAction('show_ransomnote')} disabled={isActionInProgress || isOffline}
            className="bg-pink-950/40 hover:bg-pink-900/40 text-pink-400 border-pink-500/30">
            Note
          </ActionButton>
        </div>
      </div>

      {/* Reconnaissance & Collection */}
      <div className="flex flex-col gap-2 pt-2 border-t border-slate-800/60">
        <span className="font-mono text-[10px] text-slate-400 font-bold tracking-wider uppercase mb-1">
          RECONNAISSANCE & COLLECTION
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <ActionButton onClick={() => onAction('screenshot')} disabled={isActionInProgress || isOffline}
            className="bg-sky-950/40 hover:bg-sky-900/40 text-sky-400 border-sky-500/30">
            <Eye className="h-3.5 w-3.5" /> Screenshot
          </ActionButton>
          <ActionButton onClick={() => onAction('pslist')} disabled={isActionInProgress || isOffline}
            className="bg-violet-950/40 hover:bg-violet-900/40 text-violet-400 border-violet-500/30">
            <List className="h-3.5 w-3.5" /> PSlist
          </ActionButton>
          <ActionButton onClick={() => onAction('pskill')} disabled={isActionInProgress || isOffline}
            className="bg-orange-950/40 hover:bg-orange-900/40 text-orange-400 border-orange-500/30">
            <Skull className="h-3.5 w-3.5" /> PSkill
          </ActionButton>
          <ActionButton onClick={() => onAction('steal_browsers')} disabled={isActionInProgress || isOffline}
            className="bg-rose-950/40 hover:bg-rose-900/40 text-rose-400 border-rose-500/30">
            <Trash2 className="h-3.5 w-3.5" /> Steal
          </ActionButton>
          <ActionButton onClick={() => onAction('scare')} disabled={isActionInProgress || isOffline}
            className="bg-cyan-950/40 hover:bg-cyan-900/40 text-cyan-300 border-cyan-400/30">
            <Eye className="h-3.5 w-3.5" /> SCARE
          </ActionButton>
        </div>
      </div>

      {/* Self-Destruct */}
      <div className="flex flex-col gap-2 pt-2 border-t border-slate-800/60">
        <ActionButton onClick={() => onAction('destroy')} disabled={isActionInProgress || isOffline}
          className="bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border-rose-500/40">
          <Ban className="h-3.5 w-3.5" /> Self-Destruct
        </ActionButton>
      </div>
    </div>
  );
};

function ActionButton({ onClick, disabled, className, children }: {
  onClick: () => void;
  disabled: boolean;
  className: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`group flex items-center justify-center gap-1.5 border py-2 rounded-lg text-xs font-mono font-bold uppercase tracking-wider transition-all cursor-pointer disabled:cursor-not-allowed ${className}`}
    >
      {children}
    </button>
  );
}
