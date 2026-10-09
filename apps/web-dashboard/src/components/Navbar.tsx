import React, { useState, useRef, useEffect } from 'react';
import {
  Play,
  RotateCcw,
  Square,
  Save,
  Terminal,
  User,
  CheckCircle2,
  PanelLeftClose,
  PanelLeft,
  PanelRightClose,
  PanelRight,
  Eraser,
  Lock,
  Globe,
  LogIn,
  Sun,
  Moon,
  Laptop,
  ShieldCheck,
} from 'lucide-react';
import { KernelStatus, UserProfile } from '../types';
import { useTheme } from '../context/ThemeContext';

interface NavbarProps {
  title: string;
  onTitleChange: (newTitle: string) => void;
  kernelStatus: KernelStatus;
  isSaving: boolean;
  user: UserProfile | null;
  onRunAll: () => void;
  onRestartKernel: () => void;
  onInterruptKernel: () => void;
  onClearAllOutputs?: () => void;
  onSave: () => void;
  onLogout: () => void;
  onOpenAuthModal?: () => void;
  onOpenAdminDashboard?: () => void;
  isLeftSidebarOpen: boolean;
  onToggleLeftSidebar: () => void;
  isRightSidebarOpen: boolean;
  onToggleRightSidebar: () => void;
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
  onClearAllOutputs,
  onSave,
  onLogout,
  onOpenAuthModal,
  onOpenAdminDashboard,
  isLeftSidebarOpen,
  onToggleLeftSidebar,
  isRightSidebarOpen,
  onToggleRightSidebar,
}) => {
  const { themeMode, setThemeMode } = useTheme();
  const [showThemeMenu, setShowThemeMenu] = useState(false);
  const themeMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (themeMenuRef.current && !themeMenuRef.current.contains(e.target as Node)) {
        setShowThemeMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  return (
    <header
      style={{
        height: '56px',
        backgroundColor: 'var(--bg-navbar)',
        borderBottom: '1px solid var(--border-main)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        gap: '12px',
        zIndex: 30,
        transition: 'background-color 0.15s ease, border-color 0.15s ease',
      }}
    >
      {/* Brand & Left Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Toggle Left Sidebar */}
        <button
          onClick={onToggleLeftSidebar}
          style={{
            backgroundColor: isLeftSidebarOpen ? 'var(--btn-secondary-bg)' : 'transparent',
            border: '1px solid var(--border-secondary)',
            color: isLeftSidebarOpen ? 'var(--border-accent)' : 'var(--text-secondary)',
            borderRadius: '6px',
            padding: '6px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          title={isLeftSidebarOpen ? 'Collapse Left Sidebar' : 'Expand Left Sidebar'}
        >
          {isLeftSidebarOpen ? <PanelLeftClose size={17} /> : <PanelLeft size={17} />}
        </button>

        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            backgroundColor: '#2563eb',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(37,99,235,0.4)',
          }}
        >
          <Terminal size={18} color="#ffffff" />
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: '#3b82f6',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Cloud Studio
            </span>
            <span style={{ fontSize: '11px', color: '#64748b' }}>•</span>
            <span
              style={{
                fontSize: '11px',
                color: isSaving ? '#f59e0b' : '#10b981',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
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
              color: 'var(--text-main)',
              fontSize: '14px',
              fontWeight: 600,
              padding: '2px 0',
              cursor: 'text',
              width: '240px',
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
            backgroundColor: 'var(--btn-secondary-bg)',
            color: 'var(--text-main)',
            border: '1px solid var(--btn-secondary-border)',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer',
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
            backgroundColor: 'var(--btn-secondary-bg)',
            color: 'var(--btn-secondary-text)',
            border: '1px solid var(--btn-secondary-border)',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer',
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
            backgroundColor: 'var(--btn-secondary-bg)',
            color: 'var(--btn-secondary-text)',
            border: '1px solid var(--btn-secondary-border)',
            padding: '6px 10px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer',
          }}
          title="Interrupt Execution"
        >
          <Square size={14} color="#ef4444" />
        </button>

        {onClearAllOutputs && (
          <button
            onClick={onClearAllOutputs}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--btn-secondary-bg)',
              color: 'var(--btn-secondary-text)',
              border: '1px solid var(--btn-secondary-border)',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
            title="Clear all cell outputs in notebook"
          >
            <Eraser size={14} color="#f59e0b" />
            Clear Outputs
          </button>
        )}

        <button
          onClick={onSave}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'var(--btn-secondary-bg)',
            color: 'var(--btn-secondary-text)',
            border: '1px solid var(--btn-secondary-border)',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer',
          }}
          title="Save Notebook"
        >
          <Save size={14} />
          Save
        </button>
      </div>

      {/* Right Controls: Kernel Status, User Profile, Right Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Kernel Status Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '4px 10px',
            backgroundColor: '#1e293b',
            borderRadius: '999px',
            border: '1px solid #334155',
            fontSize: '12px',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor:
                kernelStatus === 'idle'
                  ? '#10b981'
                  : kernelStatus === 'busy'
                  ? '#f59e0b'
                  : '#ef4444',
            }}
          />
          <span style={{ color: '#94a3b8', textTransform: 'capitalize' }}>
            Python 3 ({kernelStatus})
          </span>
        </div>

        {/* Workspace Mode Indicator */}
        {user ? (
          <div
            data-testid="workspace-indicator-private"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 9px',
              backgroundColor: '#064e3b',
              border: '1px solid #059669',
              borderRadius: '6px',
              fontSize: '11.5px',
              fontWeight: 600,
              color: '#a7f3d0',
            }}
            title="Private Workspace: Your files are secure and private."
          >
            <Lock size={12} color="#34d399" />
            <span>Signed In — Private Workspace</span>
          </div>
        ) : (
          <div
            data-testid="workspace-indicator-public"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 9px',
              backgroundColor: '#1e293b',
              border: '1px solid #3b82f6',
              borderRadius: '6px',
              fontSize: '11.5px',
              fontWeight: 600,
              color: '#38bdf8',
            }}
            title="Public Workspace: Files created without login are public. Sign in to create private files."
          >
            <Globe size={12} color="#38bdf8" />
            <span>Guest Mode — Public Workspace</span>
          </div>
        )}

        {/* User Info & Logout OR Guest Sign In */}
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: '#e2e8f0',
                fontSize: '13px',
              }}
            >
              <User size={15} color="#94a3b8" />
              <span>{user.full_name}</span>
              <span
                style={{
                  fontSize: '10px',
                  padding: '2px 6px',
                  backgroundColor: '#334155',
                  borderRadius: '4px',
                  color: '#cbd5e1',
                  textTransform: 'uppercase',
                }}
              >
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
                padding: '4px 6px',
              }}
            >
              Sign out
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuthModal}
            data-testid="signin-button"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '5px 12px',
              backgroundColor: '#2563eb',
              border: 'none',
              borderRadius: '6px',
              color: '#ffffff',
              fontSize: '12.5px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'background-color 0.15s ease',
            }}
          >
            <LogIn size={13} /> Sign In
          </button>
        )}

        {/* Super Admin Console Button */}
        {user && (user.role === 'super_admin' || user.role === 'admin') && onOpenAdminDashboard && (
          <button
            onClick={onOpenAdminDashboard}
            data-testid="admin-panel-btn"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '4px 10px',
              backgroundColor: '#451a03',
              border: '1px solid #d97706',
              borderRadius: '6px',
              color: '#fef3c7',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
            title="Open Super Admin Console"
          >
            <ShieldCheck size={14} color="#f59e0b" />
            <span>Admin</span>
          </button>
        )}

        {/* Theme Switcher */}
        <div style={{ position: 'relative' }} ref={themeMenuRef}>
          <button
            onClick={() => setShowThemeMenu((prev) => !prev)}
            data-testid="theme-toggle-btn"
            id="theme-switcher-btn"
            style={{
              backgroundColor: 'var(--btn-secondary-bg)',
              border: '1px solid var(--btn-secondary-border)',
              color: 'var(--btn-secondary-text)',
              borderRadius: '6px',
              padding: '6px 8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
            }}
            title={`Current Theme: ${themeMode.toUpperCase()} (Click to change)`}
          >
            {themeMode === 'system' ? (
              <Laptop size={14} color="#38bdf8" />
            ) : themeMode === 'light' ? (
              <Sun size={14} color="#f59e0b" />
            ) : (
              <Moon size={14} color="#818cf8" />
            )}
            <span style={{ textTransform: 'capitalize' }}>{themeMode}</span>
          </button>

          {showThemeMenu && (
            <div
              data-testid="theme-dropdown-menu"
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                backgroundColor: 'var(--dropdown-bg)',
                border: '1px solid var(--dropdown-border)',
                borderRadius: '8px',
                padding: '4px',
                boxShadow: '0 10px 25px -5px rgba(0,0,0,0.3)',
                zIndex: 50,
                minWidth: '130px',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
              }}
            >
              {[
                { id: 'system', label: 'System', icon: Laptop },
                { id: 'dark', label: 'Dark', icon: Moon },
                { id: 'light', label: 'Light', icon: Sun },
              ].map((t) => {
                const Icon = t.icon;
                const isSelected = themeMode === t.id;
                return (
                  <button
                    key={t.id}
                    data-testid={`theme-option-${t.id}`}
                    onClick={() => {
                      setThemeMode(t.id as any);
                      setShowThemeMenu(false);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '7px 10px',
                      borderRadius: '5px',
                      backgroundColor: isSelected ? 'var(--dropdown-item-selected)' : 'transparent',
                      border: 'none',
                      color: isSelected ? 'var(--dropdown-item-selected-text)' : 'var(--text-main)',
                      fontSize: '12.5px',
                      fontWeight: isSelected ? 600 : 400,
                      cursor: 'pointer',
                      textAlign: 'left',
                      width: '100%',
                    }}
                  >
                    <Icon size={14} color={isSelected ? 'var(--border-accent)' : 'var(--text-muted)'} />
                    <span>{t.label}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Toggle Right Sidebar */}
        <button
          onClick={onToggleRightSidebar}
          style={{
            backgroundColor: isRightSidebarOpen ? 'var(--btn-secondary-bg)' : 'transparent',
            border: '1px solid var(--border-secondary)',
            color: isRightSidebarOpen ? 'var(--border-accent)' : 'var(--text-secondary)',
            borderRadius: '6px',
            padding: '6px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          title={isRightSidebarOpen ? 'Collapse File Editor' : 'Expand File Editor'}
        >
          {isRightSidebarOpen ? <PanelRightClose size={17} /> : <PanelRight size={17} />}
        </button>
      </div>
    </header>
  );
};
