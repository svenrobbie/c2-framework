import React, { useState, useEffect } from 'react';
import { ShieldAlert, KeyRound, Lock, Unlock, Power } from 'lucide-react';

interface LoginPageProps {
  needsSetup: boolean;
  error?: string;
  onUnlock: (password: string) => void;
  onSetup: (password: string) => void;
  onErrorClear: () => void;
  connected: boolean;
}

export const LoginPage: React.FC<LoginPageProps> = ({ needsSetup, error, onUnlock, onSetup, onErrorClear, connected }) => {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [localError, setLocalError] = useState('');
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (error) {
      setSubmitted(false);
      setLocalError('');
    }
  }, [error]);

  useEffect(() => {
    setSubmitted(false);
    setLocalError('');
    setPassword('');
    setConfirm('');
  }, [needsSetup]);

  const displayError = error || localError;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError('');
    onErrorClear();

    if (!password) {
      setLocalError('Password is required');
      return;
    }

    if (needsSetup) {
      if (password.length < 4) {
        setLocalError('Password must be at least 4 characters');
        return;
      }
      if (password !== confirm) {
        setLocalError('Passwords do not match');
        return;
      }
      setSubmitted(true);
      onSetup(password);
    } else {
      setSubmitted(true);
      onUnlock(password);
    }
  };

  const title = needsSetup ? 'SET INITIAL ACCESS PASSWORD' : 'C2 INTERFACE LOCKED';
  const subtitle = needsSetup
    ? 'Configure master password to encrypt the database'
    : 'Enter master password to unlock the command interface';

  return (
    <div className="min-h-screen text-slate-100 font-mono flex flex-col items-center justify-center bg-[#05070a] p-6 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(rgba(13,110,253,0.04)_1px,transparent_1px)] bg-[size:16px_16px] pointer-events-none"></div>

      <div className="w-full max-w-md bg-slate-950 border-2 border-cyan-500/20 rounded-xl p-8 shadow-2xl relative z-10">
        <div className="flex items-center gap-3 border-b border-cyan-500/10 pb-4 mb-6">
          <div className="h-10 w-10 bg-cyan-900/20 text-cyan-400 border border-cyan-500/30 rounded-lg flex items-center justify-center">
            <span className="font-mono text-xs font-bold">RB</span>
          </div>
          <div>
            <h1 className="text-sm font-bold text-cyan-400 tracking-wider">ROGUEBYTE C2</h1>
            <p className="text-[9px] text-slate-500 uppercase tracking-widest mt-0.5">Persistent Command & Control</p>
          </div>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <div className={`p-2 rounded-lg ${needsSetup ? 'bg-amber-500/10 text-amber-400' : 'bg-rose-500/10 text-rose-400'}`}>
            {needsSetup ? <KeyRound className="h-5 w-5" /> : <Lock className="h-5 w-5" />}
          </div>
          <div>
            <h2 className="text-xs font-bold text-slate-200 tracking-wider uppercase">{title}</h2>
            <p className="text-[10px] text-slate-500 mt-0.5">{subtitle}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1.5">
              Master Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter master password"
              className="w-full bg-slate-900/80 border border-slate-800 rounded-lg px-3 py-2.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/60 font-mono transition-colors"
              autoFocus
            />
          </div>

          {needsSetup && (
            <div>
              <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1.5">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Re-enter master password"
                className="w-full bg-slate-900/80 border border-slate-800 rounded-lg px-3 py-2.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/60 font-mono transition-colors"
              />
            </div>
          )}

          {displayError && (
            <div className="bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2 text-xs text-rose-400 flex items-center gap-2">
              <ShieldAlert className="h-3.5 w-3.5 shrink-0" />
              {displayError}
            </div>
          )}

          <button
            type="submit"
            disabled={submitted}
            className="w-full py-3 bg-cyan-500 hover:bg-cyan-400 disabled:bg-cyan-500/40 disabled:cursor-not-allowed text-slate-950 font-bold rounded-lg text-xs tracking-wider uppercase transition cursor-pointer flex items-center justify-center gap-2 shadow shadow-cyan-500/20 font-sans"
          >
            {needsSetup ? (
              <><KeyRound className="h-4 w-4" /> Configure & Unlock</>
            ) : (
              <><Unlock className="h-4 w-4" /> Unlock Interface</>
            )}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-800/60 flex items-center justify-between text-[9px] text-slate-600">
          <span className="font-mono">
            {connected ? (
              <span className="text-emerald-500">Secure Tunnel Active</span>
            ) : (
              <span className="text-rose-500">Disconnected</span>
            )}
          </span>
          <span className="font-mono">{needsSetup ? 'First-Time Setup' : 'Locked'}</span>
        </div>
      </div>
    </div>
  );
};
