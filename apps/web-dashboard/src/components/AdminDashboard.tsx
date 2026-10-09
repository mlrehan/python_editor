import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Users,
  Package,
  Cpu,
  HardDrive,
  FileText,
  Settings,
  Trash2,
  Plus,
  Search,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  X,
  Folder,
  FileCode,
  Activity,
  UserCheck,
} from 'lucide-react';
import { api } from '../services/api';
import { AdminStats, AdminPackageItem, AdminRuntimeItem, AdminWorkspaceItem, AdminAuditItem } from '../types';
import { ErrorBoundary } from './ErrorBoundary';

interface AdminDashboardProps {
  isOpen: boolean;
  onClose: () => void;
  currentUserEmail?: string;
}

type TabType = 'overview' | 'users' | 'packages' | 'runtimes' | 'workspaces' | 'audit' | 'settings';

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ isOpen, onClose, currentUserEmail }) => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Overview State
  const [stats, setStats] = useState<AdminStats | null>(null);

  // Users State
  const [users, setUsers] = useState<any[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [showCreateUserModal, setShowCreateUserModal] = useState(false);
  const [newUser, setNewUser] = useState({ email: '', username: '', full_name: '', password: '', role: 'student', can_manage_packages: false });
  const [editingUser, setEditingUser] = useState<any | null>(null);
  const [resetPwdUser, setResetPwdUser] = useState<any | null>(null);
  const [newPassword, setNewPassword] = useState('');

  // Packages State
  const [packages, setPackages] = useState<AdminPackageItem[]>([]);
  const [packageSearch, setPackageSearch] = useState('');
  const [newPkgName, setNewPkgName] = useState('');
  const [installingPkg, setInstallingPkg] = useState(false);

  // Runtimes State
  const [runtimes, setRuntimes] = useState<AdminRuntimeItem[]>([]);
  const [clearingRuntime, setClearingRuntime] = useState(false);

  // Workspaces State
  const [workspaces, setWorkspaces] = useState<AdminWorkspaceItem[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<AdminWorkspaceItem | null>(null);

  // Audit State
  const [auditLogs, setAuditLogs] = useState<AdminAuditItem[]>([]);

  // Profile Settings State
  const [profileForm, setProfileForm] = useState({
    email: '',
    username: '',
    current_password: '',
    new_password: '',
  });

  const notify = (text: string, type: 'success' | 'error') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 5000);
  };

  useEffect(() => {
    if (isOpen) {
      loadTabData(activeTab);
    }
  }, [isOpen, activeTab]);

  const loadTabData = async (tab: TabType) => {
    setLoading(true);
    try {
      if (tab === 'overview') {
        const data = await api.getAdminStats();
        setStats(data || null);
      } else if (tab === 'users') {
        const data = await api.getAdminUsers(1, 100, userSearch);
        setUsers(Array.isArray(data) ? data : data?.users || []);
      } else if (tab === 'packages') {
        const data = await api.getAdminPackages(packageSearch);
        setPackages(Array.isArray(data) ? data : data?.packages || []);
      } else if (tab === 'runtimes') {
        const data = await api.getAdminRuntimes();
        setRuntimes(Array.isArray(data) ? data : data?.runtimes || []);
      } else if (tab === 'workspaces') {
        const data = await api.getAdminWorkspaces();
        const wsList = Array.isArray(data) ? data : data?.workspaces || [];
        setWorkspaces(wsList);
        if (wsList.length > 0 && !selectedWorkspace) {
          setSelectedWorkspace(wsList[0]);
        }
      } else if (tab === 'audit') {
        const data = await api.getAdminAuditLogs(100);
        setAuditLogs(Array.isArray(data) ? data : data?.logs || []);
      }
    } catch (err: any) {
      notify(err.message || 'Failed to load data', 'error');
    } finally {
      setLoading(false);
    }
  };

  // User Actions
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createAdminUser(newUser);
      notify(`User ${newUser.email} created successfully`, 'success');
      setShowCreateUserModal(false);
      setNewUser({ email: '', username: '', full_name: '', password: '', role: 'student', can_manage_packages: false });
      loadTabData('users');
    } catch (err: any) {
      notify(err.message || 'Failed to create user', 'error');
    }
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    try {
      await api.updateAdminUser(editingUser.id, {
        role: editingUser.role,
        is_active: editingUser.is_active,
        can_manage_packages: editingUser.can_manage_packages,
        full_name: editingUser.full_name,
      });
      notify(`User ${editingUser.email} updated successfully`, 'success');
      setEditingUser(null);
      loadTabData('users');
    } catch (err: any) {
      notify(err.message || 'Failed to update user', 'error');
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetPwdUser) return;
    try {
      await api.resetUserPassword(resetPwdUser.id, newPassword);
      notify(`Password for ${resetPwdUser.email} reset successfully`, 'success');
      setResetPwdUser(null);
      setNewPassword('');
    } catch (err: any) {
      notify(err.message || 'Failed to reset password', 'error');
    }
  };

  const handleDeleteUser = async (userId: string, email: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete user "${email}"? This action cannot be undone.`)) return;
    try {
      await api.deleteUser(userId);
      notify(`User ${email} deleted successfully`, 'success');
      loadTabData('users');
    } catch (err: any) {
      notify(err.message || 'Failed to delete user', 'error');
    }
  };

  // Package Actions
  const handleInstallPackage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPkgName.trim()) return;
    setInstallingPkg(true);
    try {
      await api.installPackage(newPkgName.trim());
      notify(`Package "${newPkgName}" installed successfully`, 'success');
      setNewPkgName('');
      loadTabData('packages');
    } catch (err: any) {
      notify(err.message || 'Failed to install package', 'error');
    } finally {
      setInstallingPkg(false);
    }
  };

  const handleUninstallPackage = async (pkgName: string) => {
    if (!window.confirm(`Are you sure you want to uninstall package "${pkgName}"?`)) return;
    setInstallingPkg(true);
    try {
      await api.uninstallPackage(pkgName);
      notify(`Package "${pkgName}" uninstalled successfully`, 'success');
      loadTabData('packages');
    } catch (err: any) {
      notify(err.message || 'Failed to uninstall package', 'error');
    } finally {
      setInstallingPkg(false);
    }
  };

  // Runtime Actions
  const handleClearRuntime = async (sessionId?: string, clearAll = false) => {
    const confirmMsg = clearAll
      ? 'Are you sure you want to terminate ALL running Python kernels? All unsaved in-memory variables across all users will be cleared.'
      : `Terminate kernel session "${sessionId}" and free its memory?`;
    if (!window.confirm(confirmMsg)) return;

    setClearingRuntime(true);
    try {
      const res = await api.clearRuntimes(sessionId, clearAll);
      notify(res.message || 'Runtime memory cleared successfully', 'success');
      loadTabData('runtimes');
    } catch (err: any) {
      notify(err.message || 'Failed to clear runtime', 'error');
    } finally {
      setClearingRuntime(false);
    }
  };

  // Workspace File Delete
  const handleDeleteWorkspaceFile = async (targetPath: string, fileName: string) => {
    if (!window.confirm(`Permanently delete "${fileName}"? This cannot be recovered.`)) return;
    try {
      await api.deleteWorkspaceFile(targetPath);
      notify(`Deleted "${fileName}"`, 'success');
      loadTabData('workspaces');
    } catch (err: any) {
      notify(err.message || 'Failed to delete file', 'error');
    }
  };

  // Profile Form Submit
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {};
      if (profileForm.email) payload.email = profileForm.email;
      if (profileForm.username) payload.username = profileForm.username;
      if (profileForm.new_password) {
        if (!profileForm.current_password) {
          notify('Current password is required to set a new password', 'error');
          return;
        }
        payload.current_password = profileForm.current_password;
        payload.new_password = profileForm.new_password;
      }
      await api.updateAdminProfile(payload);
      notify('Super Admin profile updated successfully', 'success');
      setProfileForm({ email: '', username: '', current_password: '', new_password: '' });
    } catch (err: any) {
      notify(err.message || 'Failed to update profile', 'error');
    }
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backdropFilter: 'blur(4px)',
      }}
    >
      <div
        data-testid="admin-dashboard-modal"
        style={{
          width: '92vw',
          maxWidth: '1240px',
          height: '88vh',
          backgroundColor: 'var(--bg-modal)',
          borderRadius: '12px',
          border: '1px solid var(--border-secondary)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        }}
      >
        {/* Top Header */}
        <div
          style={{
            height: '56px',
            backgroundColor: 'var(--bg-sidebar-header)',
            borderBottom: '1px solid var(--border-main)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ padding: '6px', backgroundColor: '#3b82f6', borderRadius: '6px' }}>
              <ShieldCheck size={18} color="#ffffff" />
            </div>
            <div>
              <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-main)' }}>
                Enterprise Studio — Super Admin Console
              </span>
              <span style={{ marginLeft: '10px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                {currentUserEmail || 'Super Administrator'}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => loadTabData(activeTab)}
              disabled={loading}
              style={{
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                color: 'var(--text-main)',
                padding: '6px 10px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
              title="Refresh Current Tab"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
            <button
              onClick={onClose}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '6px',
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Notifications / Toast */}
        {message && (
          <div
            style={{
              padding: '10px 20px',
              backgroundColor: message.type === 'success' ? '#064e3b' : '#7f1d1d',
              color: message.type === 'success' ? '#a7f3d0' : '#fecaca',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            {message.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            <span>{message.text}</span>
          </div>
        )}

        {/* Body Layout: Sidebar Navigation + Content Panel */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* Navigation Sidebar */}
          <nav
            style={{
              width: '220px',
              backgroundColor: 'var(--bg-sidebar)',
              borderRight: '1px solid var(--border-main)',
              padding: '12px 8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
            }}
          >
            {[
              { id: 'overview', label: 'System Overview', icon: Activity },
              { id: 'users', label: 'User Management', icon: Users },
              { id: 'packages', label: 'Python Packages', icon: Package },
              { id: 'runtimes', label: 'Kernel Memory', icon: Cpu },
              { id: 'workspaces', label: 'Global Workspaces', icon: HardDrive },
              { id: 'audit', label: 'Audit Logs', icon: FileText },
              { id: 'settings', label: 'Admin Profile', icon: Settings },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as TabType)}
                  data-testid={`admin-tab-${tab.id}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '10px 12px',
                    borderRadius: '6px',
                    backgroundColor: isActive ? 'var(--bg-hover)' : 'transparent',
                    border: 'none',
                    color: isActive ? 'var(--border-accent)' : 'var(--text-secondary)',
                    fontWeight: isActive ? 600 : 500,
                    fontSize: '13px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <Icon size={16} color={isActive ? 'var(--border-accent)' : 'var(--text-muted)'} />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Tab Content Panel */}
          <main style={{ flex: 1, overflowY: 'auto', padding: '24px', backgroundColor: 'var(--bg-panel)' }}>
            <ErrorBoundary fallbackTitle="Admin Console Encountered an Issue" onClose={onClose}>
            {/* 1. OVERVIEW */}
            {activeTab === 'overview' && (() => {
              const totalUsers = stats?.total_users ?? (stats as any)?.users?.total ?? 0;
              const activeUsers = stats?.active_users ?? (stats as any)?.users?.active ?? 0;
              const totalNotebooks = stats?.total_notebooks ?? (stats as any)?.content?.total_notebooks ?? 0;
              const totalProjects = stats?.total_projects ?? 0;
              const activeKernels = stats?.active_kernels ?? (stats as any)?.runtimes?.active_kernels ?? 0;

              const usedMemGb = stats?.system_memory?.used_gb ?? ((stats as any)?.system ? Number((((stats as any).system.memory_used_mb || 0) / 1024).toFixed(1)) : 0);
              const totalMemGb = stats?.system_memory?.total_gb ?? ((stats as any)?.system ? Number((((stats as any).system.memory_total_mb || 0) / 1024).toFixed(1)) : 0);
              const availMemGb = stats?.system_memory?.available_gb ?? ((stats as any)?.system ? Number(((stats as any).system.disk_free_gb || 0).toFixed(1)) : 0);
              const memPercent = stats?.system_memory?.percent ?? (stats as any)?.system?.memory_percent ?? 0;

              const usedDiskGb = stats?.disk_usage?.used_gb ?? ((stats as any)?.system ? Number((((stats as any).system.disk_total_gb || 0) - ((stats as any).system.disk_free_gb || 0)).toFixed(1)) : 0);
              const totalDiskGb = stats?.disk_usage?.total_gb ?? (stats as any)?.system?.disk_total_gb ?? 0;
              const freeDiskGb = stats?.disk_usage?.free_gb ?? (stats as any)?.system?.disk_free_gb ?? 0;
              const diskPercent = stats?.disk_usage?.percent ?? (totalDiskGb > 0 ? Number(((usedDiskGb / totalDiskGb) * 100).toFixed(1)) : 0);

              return (
                <div>
                  <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', marginBottom: '16px' }}>
                    Platform Health & Overview
                  </h2>

                  {loading && !stats ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '240px', color: '#94a3b8', gap: '10px' }}>
                      <RefreshCw size={18} className="animate-spin" />
                      <span>Loading platform statistics...</span>
                    </div>
                  ) : !stats ? (
                    <div style={{ padding: '32px', textAlign: 'center', backgroundColor: '#131d31', borderRadius: '8px', border: '1px solid #1e293b' }}>
                      <p style={{ color: '#94a3b8', marginBottom: '16px' }}>Overview statistics are currently unavailable.</p>
                      <button
                        onClick={() => loadTabData('overview')}
                        style={{
                          backgroundColor: '#2563eb',
                          border: 'none',
                          color: '#ffffff',
                          padding: '8px 16px',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '13px',
                          fontWeight: 600,
                        }}
                      >
                        Load Statistics
                      </button>
                    </div>
                  ) : (
                    <div>
                      {/* Top Stat Cards */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
                        <div style={{ backgroundColor: '#131d31', padding: '16px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                          <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Registered Users</div>
                          <div style={{ fontSize: '24px', fontWeight: 700, color: '#38bdf8' }}>{totalUsers}</div>
                          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>{activeUsers} active</div>
                        </div>
                        <div style={{ backgroundColor: '#131d31', padding: '16px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                          <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Notebooks Created</div>
                          <div style={{ fontSize: '24px', fontWeight: 700, color: '#10b981' }}>{totalNotebooks}</div>
                        </div>
                        <div style={{ backgroundColor: '#131d31', padding: '16px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                          <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Total Projects</div>
                          <div style={{ fontSize: '24px', fontWeight: 700, color: '#a855f7' }}>{totalProjects}</div>
                        </div>
                        <div style={{ backgroundColor: '#131d31', padding: '16px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                          <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Active Kernel Sessions</div>
                          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f59e0b' }}>{activeKernels}</div>
                        </div>
                      </div>

                      {/* Hardware Metrics */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <div style={{ backgroundColor: '#131d31', padding: '20px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                            <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '14px' }}>System RAM Memory</span>
                            <span style={{ fontSize: '13px', color: '#94a3b8' }}>
                              {usedMemGb} GB / {totalMemGb} GB ({memPercent}%)
                            </span>
                          </div>
                          <div style={{ width: '100%', height: '8px', backgroundColor: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
                            <div
                              style={{
                                width: `${Math.min(100, Math.max(0, memPercent))}%`,
                                height: '100%',
                                backgroundColor: memPercent > 85 ? '#ef4444' : '#3b82f6',
                              }}
                            />
                          </div>
                          <div style={{ marginTop: '10px', fontSize: '12px', color: '#64748b' }}>
                            Available: {availMemGb} GB
                          </div>
                        </div>

                        <div style={{ backgroundColor: '#131d31', padding: '20px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                            <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '14px' }}>Server Disk Storage</span>
                            <span style={{ fontSize: '13px', color: '#94a3b8' }}>
                              {usedDiskGb} GB / {totalDiskGb} GB ({diskPercent}%)
                            </span>
                          </div>
                          <div style={{ width: '100%', height: '8px', backgroundColor: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
                            <div
                              style={{
                                width: `${Math.min(100, Math.max(0, diskPercent))}%`,
                                height: '100%',
                                backgroundColor: diskPercent > 90 ? '#ef4444' : '#10b981',
                              }}
                            />
                          </div>
                          <div style={{ marginTop: '10px', fontSize: '12px', color: '#64748b' }}>
                            Free Space: {freeDiskGb} GB
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}

            {/* 2. USER MANAGEMENT */}
            {activeTab === 'users' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ position: 'relative', width: '280px' }}>
                      <Search size={14} color="#64748b" style={{ position: 'absolute', left: '10px', top: '10px' }} />
                      <input
                        type="text"
                        placeholder="Search users by email or name..."
                        value={userSearch}
                        onChange={(e) => setUserSearch(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && loadTabData('users')}
                        style={{
                          width: '100%',
                          backgroundColor: '#1e293b',
                          border: '1px solid #334155',
                          borderRadius: '6px',
                          color: '#f8fafc',
                          padding: '7px 10px 7px 32px',
                          fontSize: '13px',
                        }}
                      />
                    </div>
                    <button
                      onClick={() => loadTabData('users')}
                      style={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        color: '#cbd5e1',
                        borderRadius: '6px',
                        padding: '7px 12px',
                        fontSize: '13px',
                        cursor: 'pointer',
                      }}
                    >
                      Filter
                    </button>
                  </div>

                  <button
                    onClick={() => setShowCreateUserModal(true)}
                    style={{
                      backgroundColor: '#2563eb',
                      border: 'none',
                      borderRadius: '6px',
                      color: '#ffffff',
                      padding: '7px 14px',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <Plus size={15} /> Add New User
                  </button>
                </div>

                {/* Users Table */}
                <div style={{ backgroundColor: '#131d31', borderRadius: '8px', border: '1px solid #1e293b', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ backgroundColor: '#1e293b', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                        <th style={{ padding: '12px 16px' }}>User</th>
                        <th style={{ padding: '12px 16px' }}>Role</th>
                        <th style={{ padding: '12px 16px' }}>Package Access</th>
                        <th style={{ padding: '12px 16px' }}>Status</th>
                        <th style={{ padding: '12px 16px' }}>Joined</th>
                        <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((u) => (
                        <tr key={u.id} style={{ borderBottom: '1px solid #1e293b', color: '#e2e8f0' }}>
                          <td style={{ padding: '12px 16px' }}>
                            <div style={{ fontWeight: 600, color: '#f8fafc' }}>{u.full_name || u.username}</div>
                            <div style={{ fontSize: '12px', color: '#64748b' }}>{u.email}</div>
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            <span
                              style={{
                                fontSize: '11px',
                                padding: '3px 8px',
                                borderRadius: '4px',
                                backgroundColor: u.role === 'super_admin' ? '#451a03' : u.role === 'admin' ? '#1e1b4b' : '#1e293b',
                                color: u.role === 'super_admin' ? '#fbbf24' : u.role === 'admin' ? '#818cf8' : '#94a3b8',
                                textTransform: 'uppercase',
                                fontWeight: 600,
                              }}
                            >
                              {u.role}
                            </span>
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            {u.can_manage_packages ? (
                              <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <UserCheck size={14} /> Enabled
                              </span>
                            ) : (
                              <span style={{ color: '#64748b' }}>Disabled</span>
                            )}
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            {u.is_active ? (
                              <span style={{ color: '#10b981' }}>Active</span>
                            ) : (
                              <span style={{ color: '#ef4444' }}>Suspended</span>
                            )}
                          </td>
                          <td style={{ padding: '12px 16px', color: '#64748b', fontSize: '12px' }}>
                            {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}
                          </td>
                          <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                              <button
                                onClick={() => setEditingUser(u)}
                                style={{
                                  backgroundColor: '#1e293b',
                                  border: '1px solid #334155',
                                  color: '#cbd5e1',
                                  padding: '4px 8px',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '11px',
                                }}
                                title="Edit Role & Permissions"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => setResetPwdUser(u)}
                                style={{
                                  backgroundColor: '#1e293b',
                                  border: '1px solid #334155',
                                  color: '#f59e0b',
                                  padding: '4px 8px',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '11px',
                                }}
                                title="Reset Password"
                              >
                                Reset Pwd
                              </button>
                              {u.role !== 'super_admin' && (
                                <button
                                  onClick={() => handleDeleteUser(u.id, u.email)}
                                  style={{
                                    backgroundColor: '#450a0a',
                                    border: '1px solid #7f1d1d',
                                    color: '#f87171',
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '11px',
                                  }}
                                  title="Delete User"
                                >
                                  Delete
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 3. PACKAGES */}
            {activeTab === 'packages' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  {/* Search */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ position: 'relative', width: '280px' }}>
                      <Search size={14} color="#64748b" style={{ position: 'absolute', left: '10px', top: '10px' }} />
                      <input
                        type="text"
                        placeholder="Search Python packages..."
                        value={packageSearch}
                        onChange={(e) => setPackageSearch(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && loadTabData('packages')}
                        style={{
                          width: '100%',
                          backgroundColor: '#1e293b',
                          border: '1px solid #334155',
                          borderRadius: '6px',
                          color: '#f8fafc',
                          padding: '7px 10px 7px 32px',
                          fontSize: '13px',
                        }}
                      />
                    </div>
                    <button
                      onClick={() => loadTabData('packages')}
                      style={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        color: '#cbd5e1',
                        borderRadius: '6px',
                        padding: '7px 12px',
                        fontSize: '13px',
                        cursor: 'pointer',
                      }}
                    >
                      Filter
                    </button>
                  </div>

                  {/* Install Package Form */}
                  <form onSubmit={handleInstallPackage} style={{ display: 'flex', gap: '8px' }}>
                    <input
                      type="text"
                      placeholder="e.g. sympy==1.12 or xgboost"
                      value={newPkgName}
                      onChange={(e) => setNewPkgName(e.target.value)}
                      style={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '6px',
                        color: '#f8fafc',
                        padding: '7px 12px',
                        fontSize: '13px',
                        width: '240px',
                      }}
                    />
                    <button
                      type="submit"
                      disabled={installingPkg || !newPkgName.trim()}
                      style={{
                        backgroundColor: '#2563eb',
                        border: 'none',
                        borderRadius: '6px',
                        color: '#ffffff',
                        padding: '7px 14px',
                        fontSize: '13px',
                        fontWeight: 600,
                        cursor: installingPkg ? 'default' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      <Plus size={14} />
                      {installingPkg ? 'Installing...' : 'Install via Pip'}
                    </button>
                  </form>
                </div>

                {/* Packages Table */}
                <div style={{ backgroundColor: '#131d31', borderRadius: '8px', border: '1px solid #1e293b', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ backgroundColor: '#1e293b', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                        <th style={{ padding: '12px 16px' }}>Package Name</th>
                        <th style={{ padding: '12px 16px' }}>Version</th>
                        <th style={{ padding: '12px 16px' }}>Protected Baseline</th>
                        <th style={{ padding: '12px 16px' }}>Description</th>
                        <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {packages.map((pkg) => (
                        <tr key={pkg.name} style={{ borderBottom: '1px solid #1e293b', color: '#e2e8f0' }}>
                          <td style={{ padding: '12px 16px', fontWeight: 600, color: '#38bdf8' }}>{pkg.name}</td>
                          <td style={{ padding: '12px 16px', fontFamily: 'monospace' }}>{pkg.version}</td>
                          <td style={{ padding: '12px 16px' }}>
                            {pkg.is_protected ? (
                              <span style={{ fontSize: '11px', padding: '2px 6px', backgroundColor: '#064e3b', color: '#34d399', borderRadius: '4px' }}>
                                Core Baseline
                              </span>
                            ) : (
                              <span style={{ fontSize: '11px', padding: '2px 6px', backgroundColor: '#1e293b', color: '#94a3b8', borderRadius: '4px' }}>
                                Optional
                              </span>
                            )}
                          </td>
                          <td style={{ padding: '12px 16px', color: '#94a3b8', fontSize: '12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {pkg.summary || 'Python library'}
                          </td>
                          <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                            {!pkg.is_protected && (
                              <button
                                onClick={() => handleUninstallPackage(pkg.name)}
                                disabled={installingPkg}
                                style={{
                                  backgroundColor: '#450a0a',
                                  border: '1px solid #7f1d1d',
                                  color: '#f87171',
                                  padding: '4px 8px',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '11px',
                                }}
                              >
                                Uninstall
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 4. RUNTIMES & MEMORY */}
            {activeTab === 'runtimes' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>
                      Active Kernel Runtimes & Memory Management
                    </h2>
                    <p style={{ fontSize: '13px', color: '#94a3b8', marginTop: '2px' }}>
                      Inspect and terminate active IPyKernel processes to free RAM and system capacity.
                    </p>
                  </div>

                  <button
                    onClick={() => handleClearRuntime(undefined, true)}
                    disabled={clearingRuntime || runtimes.length === 0}
                    style={{
                      backgroundColor: '#dc2626',
                      border: 'none',
                      borderRadius: '6px',
                      color: '#ffffff',
                      padding: '8px 16px',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: clearingRuntime || runtimes.length === 0 ? 'default' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <Trash2 size={14} /> Clear All Runtimes (Free All Memory)
                  </button>
                </div>

                <div style={{ backgroundColor: '#131d31', borderRadius: '8px', border: '1px solid #1e293b', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ backgroundColor: '#1e293b', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                        <th style={{ padding: '12px 16px' }}>Session ID</th>
                        <th style={{ padding: '12px 16px' }}>User</th>
                        <th style={{ padding: '12px 16px' }}>PID</th>
                        <th style={{ padding: '12px 16px' }}>Memory (RAM)</th>
                        <th style={{ padding: '12px 16px' }}>CPU Usage</th>
                        <th style={{ padding: '12px 16px' }}>Idle Time</th>
                        <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runtimes.length === 0 ? (
                        <tr>
                          <td colSpan={7} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                            No active kernels running. Memory is fully optimized.
                          </td>
                        </tr>
                      ) : (
                        runtimes.map((rt) => (
                          <tr key={rt.session_id} style={{ borderBottom: '1px solid #1e293b', color: '#e2e8f0' }}>
                            <td style={{ padding: '12px 16px', fontFamily: 'monospace', color: '#38bdf8' }}>{rt.session_id}</td>
                            <td style={{ padding: '12px 16px' }}>{rt.user_email || (rt as any).user_id || 'Active User'}</td>
                            <td style={{ padding: '12px 16px', fontFamily: 'monospace' }}>{rt.pid || 'N/A'}</td>
                            <td style={{ padding: '12px 16px', fontWeight: 600, color: '#f59e0b' }}>{rt.memory_mb || 0} MB</td>
                            <td style={{ padding: '12px 16px' }}>{(rt.cpu_percent !== undefined && rt.cpu_percent !== null) ? `${rt.cpu_percent}%` : '0%'}</td>
                            <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{(rt.idle_seconds !== undefined && !isNaN(rt.idle_seconds)) ? `${Math.round(rt.idle_seconds)}s ago` : 'Active'}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                              <button
                                onClick={() => handleClearRuntime(rt.session_id, false)}
                                disabled={clearingRuntime}
                                style={{
                                  backgroundColor: '#1e293b',
                                  border: '1px solid #334155',
                                  color: '#f87171',
                                  padding: '4px 10px',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '11px',
                                }}
                              >
                                Free Memory
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 5. WORKSPACES & GLOBAL FILES */}
            {activeTab === 'workspaces' && (
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', marginBottom: '8px' }}>
                  Global Workspace & File Management
                </h2>
                <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '16px' }}>
                  Super administrators can inspect all public guest workspaces and isolated user workspaces, and delete unwanted files globally.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '16px' }}>
                  {/* Workspace List */}
                  <div style={{ backgroundColor: '#131d31', borderRadius: '8px', border: '1px solid #1e293b', padding: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '8px' }}>
                      WORKSPACES ({workspaces.length})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {workspaces.map((ws) => (
                        <button
                          key={ws.id}
                          onClick={() => setSelectedWorkspace(ws)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '8px 10px',
                            backgroundColor: selectedWorkspace?.id === ws.id ? '#1e293b' : 'transparent',
                            border: 'none',
                            borderRadius: '6px',
                            color: selectedWorkspace?.id === ws.id ? '#38bdf8' : '#e2e8f0',
                            fontSize: '13px',
                            cursor: 'pointer',
                            textAlign: 'left',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                            <Folder size={14} color={ws.type === 'public' || (ws as any).is_public ? '#38bdf8' : '#10b981'} />
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ws.name || (ws as any).owner || ws.id}</span>
                          </div>
                          <span style={{ fontSize: '11px', color: '#64748b' }}>{ws.item_count ?? (ws as any).file_count ?? ((ws.files && ws.files.length) || 0)} items</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Files inside Selected Workspace */}
                  <div style={{ backgroundColor: '#131d31', borderRadius: '8px', border: '1px solid #1e293b', overflow: 'hidden' }}>
                    <div style={{ padding: '12px 16px', backgroundColor: '#1e293b', borderBottom: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>
                        Files in: {selectedWorkspace?.name || (selectedWorkspace as any)?.owner || selectedWorkspace?.id || 'Public Workspace'} ({selectedWorkspace?.path || selectedWorkspace?.id || 'Root'})
                      </span>
                      <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                        Size: {selectedWorkspace?.total_size_mb ?? ((selectedWorkspace as any)?.total_size_kb ? Number(((selectedWorkspace as any).total_size_kb / 1024).toFixed(2)) : 0)} MB
                      </span>
                    </div>

                    <div style={{ padding: '8px' }}>
                      {(selectedWorkspace?.files || []).length === 0 ? (
                        <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                          Workspace is empty.
                        </div>
                      ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                          <thead>
                            <tr style={{ color: '#94a3b8', borderBottom: '1px solid #1e293b' }}>
                              <th style={{ padding: '8px 12px' }}>Name</th>
                              <th style={{ padding: '8px 12px' }}>Type</th>
                              <th style={{ padding: '8px 12px' }}>Size</th>
                              <th style={{ padding: '8px 12px', textAlign: 'right' }}>Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(selectedWorkspace?.files || []).map((file) => (
                              <tr key={file.path} style={{ borderBottom: '1px solid #1e293b', color: '#e2e8f0' }}>
                                <td style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  {file.is_dir ? <Folder size={14} color="#f59e0b" /> : <FileCode size={14} color="#38bdf8" />}
                                  {file.name}
                                </td>
                                <td style={{ padding: '8px 12px', color: '#94a3b8', fontSize: '12px' }}>
                                  {file.is_dir ? 'Directory' : 'File'}
                                </td>
                                <td style={{ padding: '8px 12px', color: '#94a3b8', fontSize: '12px' }}>
                                  {file.is_dir ? '-' : `${(file.size / 1024).toFixed(1)} KB`}
                                </td>
                                <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                                  <button
                                    onClick={() => handleDeleteWorkspaceFile(file.path, file.name)}
                                    style={{
                                      backgroundColor: '#450a0a',
                                      border: '1px solid #7f1d1d',
                                      color: '#f87171',
                                      padding: '3px 8px',
                                      borderRadius: '4px',
                                      cursor: 'pointer',
                                      fontSize: '11px',
                                    }}
                                  >
                                    Delete
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 6. AUDIT LOGS */}
            {activeTab === 'audit' && (
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', marginBottom: '16px' }}>
                  Super Admin Audit Log
                </h2>

                <div style={{ backgroundColor: '#131d31', borderRadius: '8px', border: '1px solid #1e293b', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ backgroundColor: '#1e293b', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                        <th style={{ padding: '12px 16px' }}>Timestamp</th>
                        <th style={{ padding: '12px 16px' }}>Action</th>
                        <th style={{ padding: '12px 16px' }}>Resource Type</th>
                        <th style={{ padding: '12px 16px' }}>Target ID</th>
                        <th style={{ padding: '12px 16px' }}>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.length === 0 ? (
                        <tr>
                          <td colSpan={5} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                            No audit log events recorded yet.
                          </td>
                        </tr>
                      ) : (
                        auditLogs.map((log) => (
                          <tr key={log.id} style={{ borderBottom: '1px solid #1e293b', color: '#e2e8f0' }}>
                            <td style={{ padding: '12px 16px', color: '#94a3b8', fontSize: '12px' }}>
                              {log.timestamp || (log as any).created_at ? new Date(log.timestamp || (log as any).created_at).toLocaleString() : 'N/A'}
                            </td>
                            <td style={{ padding: '12px 16px', fontWeight: 600, color: '#38bdf8' }}>{log.action}</td>
                            <td style={{ padding: '12px 16px', textTransform: 'capitalize' }}>{log.resource_type}</td>
                            <td style={{ padding: '12px 16px', fontFamily: 'monospace', fontSize: '12px' }}>{log.resource_id || '-'}</td>
                            <td style={{ padding: '12px 16px', fontFamily: 'monospace', fontSize: '11px', color: '#cbd5e1' }}>
                              {typeof log.details === 'object' ? JSON.stringify(log.details) : String(log.details || (log as any).details_json || '{}')}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 7. SETTINGS / ADMIN PROFILE */}
            {activeTab === 'settings' && (
              <div style={{ maxWidth: '600px' }}>
                <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', marginBottom: '8px' }}>
                  Super Admin Credentials & Profile
                </h2>
                <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '20px' }}>
                  Update your Super Admin login credentials. Changed passwords take effect immediately in the database and persist permanently across server restarts.
                </p>

                <form onSubmit={handleUpdateProfile} style={{ backgroundColor: '#131d31', padding: '24px', borderRadius: '8px', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
                      Admin Email
                    </label>
                    <input
                      type="email"
                      placeholder="admin@example.com"
                      value={profileForm.email}
                      onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                      style={{
                        width: '100%',
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '6px',
                        color: '#f8fafc',
                        padding: '8px 12px',
                        fontSize: '13px',
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
                      Admin Username
                    </label>
                    <input
                      type="text"
                      placeholder="admin_super"
                      value={profileForm.username}
                      onChange={(e) => setProfileForm({ ...profileForm, username: e.target.value })}
                      style={{
                        width: '100%',
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '6px',
                        color: '#f8fafc',
                        padding: '8px 12px',
                        fontSize: '13px',
                      }}
                    />
                  </div>

                  <hr style={{ borderColor: '#1e293b', margin: '8px 0' }} />

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
                      Current Password (Required only if changing password)
                    </label>
                    <input
                      type="password"
                      placeholder="••••••••••••"
                      value={profileForm.current_password}
                      onChange={(e) => setProfileForm({ ...profileForm, current_password: e.target.value })}
                      style={{
                        width: '100%',
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '6px',
                        color: '#f8fafc',
                        padding: '8px 12px',
                        fontSize: '13px',
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
                      New Password (Minimum 8 characters)
                    </label>
                    <input
                      type="password"
                      placeholder="••••••••••••"
                      value={profileForm.new_password}
                      onChange={(e) => setProfileForm({ ...profileForm, new_password: e.target.value })}
                      style={{
                        width: '100%',
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '6px',
                        color: '#f8fafc',
                        padding: '8px 12px',
                        fontSize: '13px',
                      }}
                    />
                  </div>

                  <button
                    type="submit"
                    style={{
                      backgroundColor: '#2563eb',
                      border: 'none',
                      borderRadius: '6px',
                      color: '#ffffff',
                      padding: '10px 16px',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      alignSelf: 'flex-start',
                      marginTop: '8px',
                    }}
                  >
                    Save Changes
                  </button>
                </form>
              </div>
            )}
            </ErrorBoundary>
          </main>
        </div>
      </div>

      {/* CREATE USER MODAL */}
      {showCreateUserModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 110, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <form onSubmit={handleCreateUser} style={{ backgroundColor: '#131d31', border: '1px solid #334155', borderRadius: '8px', padding: '24px', width: '400px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ fontSize: '16px', color: '#f8fafc', fontWeight: 600 }}>Create New User</h3>
            <input
              type="email"
              placeholder="Email address"
              required
              value={newUser.email}
              onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
              style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', padding: '8px 12px', fontSize: '13px' }}
            />
            <input
              type="text"
              placeholder="Username"
              required
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', padding: '8px 12px', fontSize: '13px' }}
            />
            <input
              type="text"
              placeholder="Full Name"
              value={newUser.full_name}
              onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
              style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', padding: '8px 12px', fontSize: '13px' }}
            />
            <input
              type="password"
              placeholder="Password (min 8 chars)"
              required
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
              style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', padding: '8px 12px', fontSize: '13px' }}
            />
            <select
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
              style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', padding: '8px 12px', fontSize: '13px' }}
            >
              <option value="student">Student</option>
              <option value="instructor">Instructor</option>
              <option value="admin">Admin</option>
              <option value="super_admin">Super Admin</option>
            </select>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#cbd5e1', fontSize: '12px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={newUser.can_manage_packages}
                onChange={(e) => setNewUser({ ...newUser, can_manage_packages: e.target.checked })}
              />
              Grant Package Management Permission
            </label>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
              <button type="button" onClick={() => setShowCreateUserModal(false)} style={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#94a3b8', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
                Cancel
              </button>
              <button type="submit" style={{ backgroundColor: '#2563eb', border: 'none', color: '#ffffff', padding: '6px 16px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}>
                Create
              </button>
            </div>
          </form>
        </div>
      )}

      {/* EDIT USER MODAL */}
      {editingUser && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 110, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <form onSubmit={handleUpdateUser} style={{ backgroundColor: '#131d31', border: '1px solid #334155', borderRadius: '8px', padding: '24px', width: '400px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ fontSize: '16px', color: '#f8fafc', fontWeight: 600 }}>Edit User: {editingUser.email}</h3>
            <input
              type="text"
              placeholder="Full Name"
              value={editingUser.full_name || ''}
              onChange={(e) => setEditingUser({ ...editingUser, full_name: e.target.value })}
              style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', padding: '8px 12px', fontSize: '13px' }}
            />
            <select
              value={editingUser.role}
              onChange={(e) => setEditingUser({ ...editingUser, role: e.target.value })}
              style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', padding: '8px 12px', fontSize: '13px' }}
            >
              <option value="student">Student</option>
              <option value="instructor">Instructor</option>
              <option value="admin">Admin</option>
              <option value="super_admin">Super Admin</option>
            </select>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#cbd5e1', fontSize: '12px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={editingUser.can_manage_packages || false}
                onChange={(e) => setEditingUser({ ...editingUser, can_manage_packages: e.target.checked })}
              />
              Package Management Permission
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#cbd5e1', fontSize: '12px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={editingUser.is_active}
                onChange={(e) => setEditingUser({ ...editingUser, is_active: e.target.checked })}
              />
              Active Account
            </label>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
              <button type="button" onClick={() => setEditingUser(null)} style={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#94a3b8', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
                Cancel
              </button>
              <button type="submit" style={{ backgroundColor: '#2563eb', border: 'none', color: '#ffffff', padding: '6px 16px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}>
                Save
              </button>
            </div>
          </form>
        </div>
      )}

      {/* RESET PASSWORD MODAL */}
      {resetPwdUser && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 110, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <form onSubmit={handleResetPassword} style={{ backgroundColor: '#131d31', border: '1px solid #334155', borderRadius: '8px', padding: '24px', width: '380px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ fontSize: '16px', color: '#f8fafc', fontWeight: 600 }}>Reset Password</h3>
            <p style={{ fontSize: '12px', color: '#94a3b8' }}>Set new password for {resetPwdUser.email}</p>
            <input
              type="password"
              placeholder="New password (min 8 chars)"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', padding: '8px 12px', fontSize: '13px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
              <button type="button" onClick={() => setResetPwdUser(null)} style={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#94a3b8', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
                Cancel
              </button>
              <button type="submit" style={{ backgroundColor: '#f59e0b', border: 'none', color: '#000000', padding: '6px 16px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}>
                Reset
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
