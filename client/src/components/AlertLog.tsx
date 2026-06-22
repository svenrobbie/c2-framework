import React, { useState, useEffect } from 'react';
import { AlertTriangle, Clock, Filter } from 'lucide-react';

interface AlertEntry {
  rule: string;
  hostname: string;
  field: string;
  value: string;
  action: string;
  timestamp: string;
}

interface AlertLogProps {
  liveEntries: AlertEntry[];
}

export const AlertLog: React.FC<AlertLogProps> = ({ liveEntries }) => {
  const [entries, setEntries] = useState<AlertEntry[]>([]);
  const [filterHost, setFilterHost] = useState('');

  useEffect(() => {
    const fetchLog = async () => {
      try {
        const url = filterHost ? `/api/triggers/log?hostname=${encodeURIComponent(filterHost)}` : '/api/triggers/log';
        const resp = await fetch(url);
        if (resp.ok) setEntries(await resp.json());
      } catch {}
    };
    fetchLog();
  }, [filterHost]);

  // Merge REST-fetched entries with live socket entries, deduplicated by rule+hostname+timestamp
  const seen = new Set<string>();
  const merged = [...entries, ...liveEntries].filter(e => {
    const key = `${e.rule}|${e.hostname}|${e.timestamp}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  // Sort by timestamp descending
  merged.sort((a, b) => b.timestamp.localeCompare(a.timestamp));

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-[10px] text-slate-500 font-bold uppercase tracking-wider flex items-center gap-2">
        <AlertTriangle className="h-3 w-3" />
        Alert History
      </h3>

      <div className="flex items-center gap-2">
        <Filter className="h-3 w-3 text-slate-500" />
        <input
          value={filterHost}
          onChange={(e) => setFilterHost(e.target.value)}
          placeholder="Filter by hostname..."
          className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/60"
        />
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-1.5">
        {merged.length === 0 && (
          <div className="text-center py-8 text-slate-600 font-mono text-xs italic">
            &lt; No alert events recorded &gt;
          </div>
        )}
        {merged.map((e, i) => (
          <div key={i} className="bg-slate-900/40 border border-slate-800/60 rounded-lg p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">{e.rule}</span>
              <span className="text-[9px] text-slate-500 font-mono flex items-center gap-1">
                <Clock className="h-2.5 w-2.5" />
                {e.timestamp}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-1 font-mono">
              {e.hostname} — {e.field} = "{e.value}"
            </p>
            <p className="text-[9px] text-slate-500 mt-0.5">Action: {e.action}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
