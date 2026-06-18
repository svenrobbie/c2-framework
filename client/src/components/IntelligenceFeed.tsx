import React, { useState, useEffect } from 'react';
import { Shield, Server, Bell, Key, Zap, CheckCircle2, AlertCircle } from 'lucide-react';
import { Victim } from '../types';

interface IntelligenceFeedProps {
  victims: Victim[];
}

export const IntelligenceFeed: React.FC<IntelligenceFeedProps> = ({ victims }) => {
  const [feedLogs, setFeedLogs] = useState<string[]>([]);

  useEffect(() => {
    const feeds = [
      "Alert: Port scan activity detected from candidate gateway.",
      "Threat Intel: Encrypted protocol signature mapped to Lazarus subgroup variant.",
      "DNS Sinkhole updated with 4 new known threat indicators.",
      "System: Kernel memory sanitization completed successfully.",
      "Operational security warning: Ensure SSH tunnels utilize key-only auth.",
      "Ransomware telemetry: Overall ransom key generation is active and isolated."
    ];
    setFeedLogs(feeds);

    const interval = setInterval(() => {
      const randomFeed = feeds[Math.floor(Math.random() * feeds.length)];
      setFeedLogs(prev => [randomFeed, ...prev.slice(0, 4)]);
    }, 12000);

    return () => clearInterval(interval);
  }, []);

  const onlineCount = victims.filter(v => v.status === 'ONLINE').length;
  const encryptedCount = victims.filter(v => v.status === 'ENCRYPTED').length;
  const watchdogCount = victims.filter(v => v.status === 'WATCHDOG').length;
  const totalVictims = victims.length;

  return (
    <div className="bg-slate-900/30 border border-slate-900 rounded-xl p-5 flex flex-col gap-5">
      <div>
        <h2 className="font-mono text-xs font-bold text-primary uppercase tracking-wider mb-1 flex items-center gap-1.5">
          <Shield className="h-4 w-4 text-cyan-400" />
          SYSTEM INTEGRITY & COMMAND INTEL
        </h2>
        <p className="text-xs text-slate-400">Real-time indicators and operational threat intelligence.</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/40 p-4 rounded-xl border border-slate-900/80">
        <div className="flex flex-col gap-1 items-center justify-center text-center p-2 rounded bg-slate-900/20 border border-slate-900/40">
          <span className="text-[10px] text-slate-500 font-mono font-bold uppercase">TOTAL TARGETS</span>
          <span className="text-xl font-bold text-primary font-mono">{totalVictims}</span>
        </div>
        <div className="flex flex-col gap-1 items-center justify-center text-center p-2 rounded bg-slate-900/20 border border-slate-900/40">
          <span className="text-[10px] text-emerald-500 font-mono font-bold uppercase">ONLINE (LIVE)</span>
          <span className="text-xl font-bold text-emerald-400 font-mono">{onlineCount}</span>
        </div>
        <div className="flex flex-col gap-1 items-center justify-center text-center p-2 rounded bg-slate-900/20 border border-slate-900/40">
          <span className="text-[10px] text-rose-500 font-mono font-bold uppercase">ENCRYPTED</span>
          <span className="text-xl font-bold text-rose-400 font-mono">{encryptedCount}</span>
        </div>
        <div className="flex flex-col gap-1 items-center justify-center text-center p-2 rounded bg-slate-900/20 border border-slate-900/40">
          <span className="text-[10px] text-amber-500 font-mono font-bold uppercase">WATCHDOG DETECTED</span>
          <span className="text-xl font-bold text-amber-400 font-mono">{watchdogCount}</span>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <span className="font-mono text-[10px] text-slate-500 font-bold tracking-wider uppercase">
          LIVE CRYPTO-ROUTINE METRICS Or SEC-Intel feed
        </span>
        <div className="flex flex-col gap-2">
          {feedLogs.map((log, index) => (
            <div key={index} className="flex gap-2.5 items-start text-xs border border-slate-900/40 bg-slate-950/20 p-2.5 rounded font-mono text-slate-300">
              {index === 0 ? (
                <Zap className="h-3.5 w-3.5 text-cyan-400 shrink-0 mt-0.5 animate-pulse" />
              ) : (
                <CheckCircle2 className="h-3.5 w-3.5 text-slate-600 shrink-0 mt-0.5" />
              )}
              <span className="leading-tight">{log}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
