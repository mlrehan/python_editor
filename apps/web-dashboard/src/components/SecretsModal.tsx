import React, { useState, useEffect } from 'react';
import { Key, Plus, Trash2, Eye, EyeOff, Save, X, Shield, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';

interface SecretsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface EnvEntry {
  id: string;
  key: string;
  value: string;
  showValue: boolean;
}

const PRESET_TEMPLATES = [
  { name: 'OpenAI', key: 'OPENAI_API_KEY', placeholder: 'sk-proj-...' },
  { name: 'Google Gemini', key: 'GEMINI_API_KEY', placeholder: 'AIzaSy...' },
  { name: 'Anthropic Claude', key: 'ANTHROPIC_API_KEY', placeholder: 'sk-ant-...' },
  { name: 'Hugging Face', key: 'HUGGINGFACE_API_KEY', placeholder: 'hf_...' },
];

export const SecretsModal: React.FC<SecretsModalProps> = ({ isOpen, onClose }) => {
  const [entries, setEntries] = useState<EnvEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadEnv();
    }
  }, [isOpen]);

  const loadEnv = async () => {
    setLoading(true);
    setStatusMsg(null);
    try {
      const data = await api.getWorkspaceEnv();
      const list: EnvEntry[] = Object.entries(data.env || {}).map(([key, val], idx) => ({
        id: `env-${idx}-${Date.now()}`,
        key,
        value: val,
        showValue: false,
      }));
      setEntries(list);
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Failed to load environment variables', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleAddEntry = (presetKey = '', presetVal = '') => {
    setEntries((prev) => [
      ...prev,
      {
        id: `env-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
        key: presetKey,
        value: presetVal,
        showValue: true,
      },
    ]);
  };

  const handleUpdateEntry = (id: string, field: 'key' | 'value', val: string) => {
    setEntries((prev) =>
      prev.map((e) => (e.id === id ? { ...e, [field]: field === 'key' ? val.toUpperCase().replace(/[^A-Z0-9_]/g, '') : val } : e))
    );
  };

  const handleToggleShow = (id: string) => {
    setEntries((prev) =>
      prev.map((e) => (e.id === id ? { ...e, showValue: !e.showValue } : e))
    );
  };

  const handleRemoveEntry = (id: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== id));
  };

  const handleSave = async () => {
    setSaving(true);
    setStatusMsg(null);
    try {
      const envDict: Record<string, string> = {};
      for (const entry of entries) {
        const k = entry.key.trim();
        if (k) {
          envDict[k] = entry.value;
        }
      }
      await api.saveWorkspaceEnv(envDict);
      setStatusMsg({
        text: 'Environment variables saved! Injected into your isolated Python kernel session.',
        type: 'success',
      });
      setTimeout(() => setStatusMsg(null), 4000);
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Failed to save environment variables', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      data-testid="secrets-modal"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(3px)',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: '720px',
          maxWidth: '92vw',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'var(--bg-modal, #1e293b)',
          borderRadius: '12px',
          border: '1px solid var(--border-secondary, #334155)',
          boxShadow: '0 25px 50px rgba(0, 0, 0, 0.5)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-main, #334155)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: '#7c3aed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Key size={16} color="#ffffff" />
            </div>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-main, #f8fafc)', margin: 0 }}>
                Workspace Secrets & AI Credentials
              </h2>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary, #94a3b8)' }}>
                Isolated kernel environment variables (.env)
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              color: 'var(--text-secondary, #94a3b8)',
              cursor: 'pointer',
              padding: '4px',
            }}
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Security Info Banner */}
        <div
          style={{
            padding: '10px 20px',
            backgroundColor: 'rgba(124, 58, 237, 0.08)',
            borderBottom: '1px solid var(--border-secondary, #334155)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '12px',
            color: '#c4b5fd',
          }}
        >
          <Shield size={14} color="#a78bfa" />
          <span>
            Keys are stored privately in your workspace and injected into your Python runtime via{' '}
            <code style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '1px 4px', borderRadius: '4px' }}>
              os.getenv("KEY")
            </code>
            . Server secrets are strictly shielded.
          </span>
        </div>

        {/* Quick-Add Templates */}
        <div
          style={{
            padding: '12px 20px',
            borderBottom: '1px solid var(--border-secondary, #334155)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flexWrap: 'wrap',
          }}
        >
          <span style={{ fontSize: '12px', color: 'var(--text-secondary, #94a3b8)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Sparkles size={13} color="#f59e0b" /> Quick Templates:
          </span>
          {PRESET_TEMPLATES.map((tmpl) => {
            const alreadyExists = entries.some((e) => e.key === tmpl.key);
            return (
              <button
                key={tmpl.key}
                disabled={alreadyExists}
                onClick={() => handleAddEntry(tmpl.key, '')}
                style={{
                  padding: '4px 10px',
                  backgroundColor: alreadyExists ? 'rgba(255,255,255,0.04)' : 'rgba(124, 58, 237, 0.15)',
                  border: alreadyExists ? '1px solid rgba(255,255,255,0.1)' : '1px solid #7c3aed',
                  color: alreadyExists ? '#64748b' : '#d8b4fe',
                  borderRadius: '6px',
                  fontSize: '11.5px',
                  cursor: alreadyExists ? 'default' : 'pointer',
                  fontWeight: 500,
                  transition: 'all 0.15s ease',
                }}
              >
                + {tmpl.name}
              </button>
            );
          })}
        </div>

        {/* Content Entries List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          {statusMsg && (
            <div
              style={{
                padding: '8px 12px',
                backgroundColor: statusMsg.type === 'success' ? '#064e3b' : '#450a0a',
                border: statusMsg.type === 'success' ? '1px solid #10b981' : '1px solid #ef4444',
                borderRadius: '6px',
                color: statusMsg.type === 'success' ? '#a7f3d0' : '#fca5a5',
                fontSize: '12.5px',
                marginBottom: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              {statusMsg.type === 'success' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
              <span>{statusMsg.text}</span>
            </div>
          )}

          {loading && (
            <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-secondary, #94a3b8)' }}>
              Loading secrets...
            </div>
          )}

          {!loading && entries.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-secondary, #94a3b8)' }}>
              <Key size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
              <p style={{ margin: 0, fontSize: '14px' }}>No environment variables configured</p>
              <p style={{ margin: '4px 0 0', fontSize: '12px' }}>
                Use a template above or click "Add Variable" to provide an AI key.
              </p>
            </div>
          )}

          {!loading && entries.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-input, rgba(255, 255, 255, 0.04))',
                    border: '1px solid var(--border-secondary, #334155)',
                    borderRadius: '8px',
                  }}
                >
                  {/* Key Input */}
                  <input
                    type="text"
                    value={entry.key}
                    placeholder="KEY_NAME"
                    onChange={(e) => handleUpdateEntry(entry.id, 'key', e.target.value)}
                    style={{
                      width: '200px',
                      padding: '6px 10px',
                      backgroundColor: 'rgba(0, 0, 0, 0.25)',
                      border: '1px solid var(--border-secondary, #475569)',
                      borderRadius: '6px',
                      color: 'var(--text-main, #f8fafc)',
                      fontSize: '12.5px',
                      fontFamily: 'monospace',
                      fontWeight: 600,
                    }}
                  />

                  <span style={{ color: 'var(--text-secondary, #94a3b8)', fontWeight: 600 }}>=</span>

                  {/* Value Input */}
                  <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <input
                      type={entry.showValue ? 'text' : 'password'}
                      value={entry.value}
                      placeholder="API Key or secret value..."
                      onChange={(e) => handleUpdateEntry(entry.id, 'value', e.target.value)}
                      style={{
                        width: '100%',
                        padding: '6px 36px 6px 10px',
                        backgroundColor: 'rgba(0, 0, 0, 0.25)',
                        border: '1px solid var(--border-secondary, #475569)',
                        borderRadius: '6px',
                        color: 'var(--text-main, #f8fafc)',
                        fontSize: '12.5px',
                        fontFamily: 'monospace',
                        boxSizing: 'border-box',
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => handleToggleShow(entry.id)}
                      style={{
                        position: 'absolute',
                        right: '8px',
                        backgroundColor: 'transparent',
                        border: 'none',
                        color: 'var(--text-secondary, #94a3b8)',
                        cursor: 'pointer',
                        padding: '2px',
                      }}
                      title={entry.showValue ? 'Hide value' : 'Show value'}
                    >
                      {entry.showValue ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>

                  {/* Remove Button */}
                  <button
                    type="button"
                    onClick={() => handleRemoveEntry(entry.id)}
                    style={{
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: '#ef4444',
                      cursor: 'pointer',
                      padding: '4px 6px',
                    }}
                    title="Remove variable"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '12px 20px',
            borderTop: '1px solid var(--border-main, #334155)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'rgba(0, 0, 0, 0.15)',
          }}
        >
          <button
            type="button"
            onClick={() => handleAddEntry()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              backgroundColor: 'transparent',
              border: '1px solid var(--border-secondary, #475569)',
              borderRadius: '6px',
              color: 'var(--text-main, #f8fafc)',
              fontSize: '12.5px',
              cursor: 'pointer',
            }}
          >
            <Plus size={14} /> Add Variable
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '6px 14px',
                backgroundColor: 'transparent',
                border: '1px solid var(--border-secondary, #475569)',
                borderRadius: '6px',
                color: 'var(--text-secondary, #94a3b8)',
                fontSize: '12.5px',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={saving}
              onClick={handleSave}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 16px',
                backgroundColor: '#2563eb',
                border: 'none',
                borderRadius: '6px',
                color: '#ffffff',
                fontSize: '12.5px',
                fontWeight: 600,
                cursor: saving ? 'default' : 'pointer',
                opacity: saving ? 0.7 : 1,
              }}
            >
              <Save size={14} />
              {saving ? 'Saving...' : 'Save Secrets'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

