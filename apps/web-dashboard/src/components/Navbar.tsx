import React from 'react';
import { Play, RotateCcw, Square, Save, Terminal, User, CheckCircle2 } from 'lucide-react';
import { KernelStatus, UserProfile } from '../types';

interface NavbarProps {
  title: string;
  onTitleChange: (newTitle: string) => void;
  kernelStatus: KernelStatus;
  isSaving: boolean;
  user: UserProfile | null;
  onRunAll: () => void;
  onRestartKernel: () => void;
  onInterruptKernel: () => void;
  onSave: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  title,
  onTitleChange,
  kernelStatus,
  isSaving,
  user,
  onRunAll,
  onRestartKernel,
  onInterruptKernel,
  onSave,
  onLogout,
}) => {
  return (
    <header style={{
      height: '56px',
      backgroundColor: '#0f172a',
      borderBottom: '1px solid #1e293b',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 16px',
      gap: '16px'
    }}>
      {/* Brand & Notebook Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '32px',
          height: '32px',
          borderRadius: '8px',
          backgroundColor: '#2563eb',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 8px rgba(37,99,235,0.4)'
        }}>
          <Terminal size={18} color="#ffffff" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Cloud Studio
            </span>
            <span style={{ fontSize: '11px', color: '#64748b' }}>•</span>
            <span style={{ fontSize: '11px', color: isSaving ? '#f59e0b' : '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
              {isSaving ? 'Saving...' : <><CheckCircle2 size={12} /> Saved</>}
            </span>
          </div>
          <input
            type="text"
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#f8fafc',
              fontSize: '14px',
              fontWeight: 600,
              padding: '2px 0',
              cursor: 'text',
              width: '260px'
            }}
          />
        </div>
      </div>

      {/* Center Execution Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={onRunAll}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#1e293b',
            color: '#f8fafc',
            border: '1px solid #334155',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
          title="Run All Cells"
        >
          <Play size={14} color="#3b82f6" fill="#3b82f6" />
          Run All
        </button>

        <button
          onClick={onRestartKernel}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#1e293b',
            color: '#94a3b8',
            border: '1px solid #334155',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
          title="Restart Python Kernel"
        >
          <RotateCcw size={14} />
          Restart
        </button>

        <button
          onClick={onInterruptKernel}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#1e293b',
            color: '#94a3b8',
            border: '1px solid #334155',
            padding: '6px 10px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
          title="Interrupt Execution"
        >
          <Square size={14} color="#ef4444" />
        </button>

        <button
          onClick={onSave}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#1e293b',
            color: '#94a3b8',
            border: '1px solid #334155',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
          title="Save Notebook"
        >
          <Save size={14} />
          Save
        </button>
      </div>

      {/* Right Kernel Status & User Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Kernel Status Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '4px 10px',
          backgroundColor: '#1e293b',
          borderRadius: '999px',
          border: '1px solid #334155',
          fontSize: '12px'
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor:
              kernelStatus === 'idle'
                ? '#10b981'
                : kernelStatus === 'busy'
                ? '#f59e0b'
                : '#ef4444'
          }} />
          <span style={{ color: '#94a3b8', textTransform: 'capitalize' }}>
            Python 3 ({kernelStatus})
          </span>
        </div>

        {/* User Info & Logout */}
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: '#e2e8f0',
              fontSize: '13px'
            }}>
              <User size={15} color="#94a3b8" />
              <span>{user.full_name}</span>
              <span style={{
                fontSize: '10px',
                padding: '2px 6px',
                backgroundColor: '#334155',
                borderRadius: '4px',
                color: '#cbd5e1',
                textTransform: 'uppercase'
              }}>
                {user.role}
              </span>
            </div>
            <button
              onClick={onLogout}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                color: '#ef4444',
                fontSize: '12px',
                cursor: 'pointer',
                padding: '4px 8px'
              }}
            >
              Sign out
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
};
