import React, { useState } from 'react';
import { HelpCircle, X, ShieldAlert, Cpu, Terminal, Radio } from 'lucide-react';

interface HelpModalProps {
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div 
        className="w-full max-w-2xl bg-slate-900 border-2 border-primary/40 rounded-xl p-6 shadow-2xl overflow-y-auto max-h-[90vh] custom-scrollbar"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-start border-b border-slate-800 pb-4 mb-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-primary" />
            <h2 className="font-mono text-sm font-bold text-primary uppercase tracking-wider">
              ROGUEBYTE OPERATOR MANUAL & HELPDESK
            </h2>
          </div>
          <button 
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="font-mono text-xs text-slate-300 space-y-4">
          <div>
            <span className="text-primary font-bold block mb-1">1. OVERVIEW</span>
            <p className="leading-relaxed text-slate-400">
              RogueByte C2 is an authoritative enterprise-grade Command and Control dashboard mock representation. It is engineered for dark visual telemetry supervision, allowing you to orchestrate active implants, broadcast commands, and keep continuous status loops.
            </p>
          </div>

          <div>
            <span className="text-primary font-bold block mb-1">2. TARGET MONITORING</span>
            <p className="leading-relaxed text-slate-400">
              The left panel provides a high-density viewport of all target hosts running under active stagers. Icons signify the agent category (Ransomware, Botnet, Industrial, Spyware, or generic Stagers). Each card tracks real-time country indicators and active beacon intervals.
            </p>
          </div>

          <div>
            <span className="text-primary font-bold block mb-1">3. EXECUTING LIVE IMPLANT TASKS</span>
            <p className="leading-relaxed text-slate-400">
              Select any target host from the monitoring directory to initiate active C2 tasks:
            </p>
            <ul className="list-disc pl-5 mt-1.5 space-y-1 text-slate-400">
              <li><strong className="text-rose-400">Encrypt:</strong> Broadside cryptographic routine on target folders. Will shift status to ENCRYPTED.</li>
              <li><strong className="text-amber-400">Decrypt:</strong> Delivers victim private keys to revert state securely.</li>
              <li><strong className="text-blue-400">Execute:</strong> Tests raw terminal command pipelines on targeted nodes.</li>
              <li><strong className="text-primary">Terminal:</strong> Attaches live terminal simulation logic.</li>
              <li><strong className="text-purple-400">Persist:</strong> Installs registry update helpers on targeted operating systems.</li>
              <li><strong className="text-cyan-400">Netinfo:</strong> Performs continuous traceroute and gateway scanning.</li>
            </ul>
          </div>

          <div>
            <span className="text-primary font-bold block mb-1">4. COMMAND TELEMETRY DECODING</span>
            <p className="leading-relaxed text-slate-400">
              All payload responses pass through the military-grade telemetry stream on the right. Logs include execution status outputs, privileges layout arrays, heartbeats, and alert signals emitted from operating system watchdogs. Keep an eye on incoming alerts!
            </p>
          </div>

          <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800/80">
            <span className="text-amber-400 font-bold block mb-1">AUTOMATED TESTING</span>
            <p className="leading-relaxed text-slate-400 text-[11px]">
              Use the <strong className="text-primary">"Toggle Auto Beacons"</strong> function at the bottom to simulate live beacons or inject alerts. It adds organic variations to resources and network payloads continuously.
            </p>
          </div>
        </div>

        <div className="flex justify-end mt-6 border-t border-slate-800 pt-4">
          <button 
            onClick={onClose}
            className="px-4 py-2 bg-primary hover:bg-primary/80 text-slate-950 font-mono font-bold rounded-lg text-xs tracking-wider uppercase transition cursor-pointer"
          >
            Acknowledge Protocols
          </button>
        </div>
      </div>
    </div>
  );
};
