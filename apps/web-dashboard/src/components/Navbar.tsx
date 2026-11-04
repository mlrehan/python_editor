import React, { useState, useRef, useEffect, useLayoutEffect } from 'react';
import {
  Play,
  RotateCcw,
  Square,
  Save,
  Terminal,
  CheckCircle2,
  Loader2,
  PanelLeftClose,
  PanelLeft,
  PanelRightClose,
  PanelRight,
  Eraser,
  Lock,
  Globe,
  LogIn,
  LogOut,
  Sun,
  Moon,
  Laptop,
  ShieldCheck,
  BookOpen,
  Key,
  HelpCircle,
  MoreHorizontal,
  ChevronDown,
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
  // True while any cell is executing: Stop is highlighted
  isExecuting?: boolean;
  onClearAllOutputs?: () => void;
  onSave: () => void;
  onLogout: () => void;
  onOpenAuthModal?: () => void;
  onOpenAdminDashboard?: () => void;
  onOpenNotebooks?: () => void;
  onOpenSecrets?: () => void;
  isRestarting?: boolean;
  isLeftSidebarOpen: boolean;
  onToggleLeftSidebar: () => void;
  isRightSidebarOpen: boolean;
  onToggleRightSidebar: () => void;
}

/*
 * Responsive tiers, measured on the bar itself (it spans the window, but measuring the element also
 * covers browser zoom and embedded views). As space shrinks, labels disappear first, then the
 * lower-priority groups move into the "More" menu; run controls, kernel status and account always stay.
 * On phones (xxs) the theme switcher and workspace indicator move into the More menu as well.
 */
type Tier = 'xxs' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
const TIER_MIN_WIDTH: Array<[Tier, number]> = [
  ['xl', 1560],
  ['lg', 1280],
  ['md', 1024],
  ['sm', 720],
  ['xs', 480],
  ['xxs', 0],
];
const TIER_RANK: Record<Tier, number> = { xxs: 0, xs: 1, sm: 2, md: 3, lg: 4, xl: 5 };

function tierForWidth(width: number): Tier {
  return (TIER_MIN_WIDTH.find(([, min]) => width >= min) ?? ['xxs', 0])[0];
}

const HELP_URL = '/python-cloud-studio-user-guide.html';

const THEME_OPTIONS = [
  { id: 'system', label: 'System', icon: Laptop },
  { id: 'dark', label: 'Dark', icon: Moon },
  { id: 'light', label: 'Light', icon: Sun },
] as const;

const KERNEL_TONE: Record<KernelStatus, 'success' | 'warning' | 'info' | 'danger'> = {
  idle: 'success',
  busy: 'warning',
  restarting: 'info',
  connecting: 'info',
  disconnected: 'danger',
};

// Closes a popover on outside pointer-down or Escape
function useDismiss(open: boolean, ref: React.RefObject<HTMLElement | null>, close: () => void) {
  const closeRef = useRef(close);
  closeRef.current = close;
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) closeRef.current();
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeRef.current();
        (ref.current?.querySelector('button') as HTMLButtonElement | null)?.focus();
      }
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open, ref]);
}

function initialsOf(name: string, email: string): string {
  const source = name.trim() || email;
  const parts = source.split(/[\s@._-]+/).filter(Boolean);
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[1][0] : '')).toUpperCase() || '?';
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
  isExecuting = false,
  onClearAllOutputs,
  onSave,
  onLogout,
  onOpenAuthModal,
  onOpenAdminDashboard,
  onOpenNotebooks,
  onOpenSecrets,
  isRestarting = false,
  isLeftSidebarOpen,
  onToggleLeftSidebar,
  isRightSidebarOpen,
  onToggleRightSidebar,
}) => {
  const { themeMode, setThemeMode } = useTheme();
  const headerRef = useRef<HTMLElement>(null);
  const [tier, setTier] = useState<Tier>(() =>
    typeof window !== 'undefined' ? tierForWidth(window.innerWidth) : 'lg'
  );
  const [openMenu, setOpenMenu] = useState<'more' | 'account' | 'theme' | null>(null);
  const moreRef = useRef<HTMLDivElement>(null);
  const accountRef = useRef<HTMLDivElement>(null);
  const themeRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const header = headerRef.current;
    if (!header) return;
    const update = () => setTier(tierForWidth(header.getBoundingClientRect().width));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(header);
    return () => observer.disconnect();
  }, []);

  const closeMenus = () => setOpenMenu(null);
  useDismiss(openMenu === 'more', moreRef, closeMenus);
  useDismiss(openMenu === 'account', accountRef, closeMenus);
  useDismiss(openMenu === 'theme', themeRef, closeMenus);
  const toggleMenu = (menu: 'more' | 'account' | 'theme') => setOpenMenu((current) => (current === menu ? null : menu));

  const atLeast = (t: Tier) => TIER_RANK[tier] >= TIER_RANK[t];
  const isAdmin = !!user && (user.role === 'super_admin' || user.role === 'admin') && !!onOpenAdminDashboard;

  // What stays in the bar at this width; everything else goes into the More / account menus
  const runLabels = atLeast('md');
  const notebookActionsInBar = atLeast('md');
  const notebookActionLabels = atLeast('lg');
  const workspaceToolsInBar = atLeast('lg');
  const workspaceToolLabels = atLeast('xl');
  const adminInBar = isAdmin && atLeast('md');
  const kernelLabel = atLeast('lg');
  const workspaceLabel = atLeast('lg');
  // Signed-in users also show the admin button and their name at xl, so only guests get the long label
  const workspaceLabelFull = atLeast('xl') && !user;
  const showBrand = atLeast('sm');
  const showSaveState = atLeast('sm');
  const statusChipsInBar = atLeast('xs');
  const themeInBar = atLeast('xs');

  const themeOptions = THEME_OPTIONS.map((t) => {
    const Icon = t.icon;
    return (
      <MenuItem
        key={t.id}
        testId={`theme-option-${t.id}`}
        icon={<Icon size={15} />}
        selected={themeMode === t.id}
        onClick={() => {
          setThemeMode(t.id);
          closeMenus();
        }}
      >
        {t.label}
      </MenuItem>
    );
  });

  const moreItems: React.ReactNode[] = [];
  if (!statusChipsInBar) {
    moreItems.push(
      <div
        key="workspace"
        className="tb-menu-status"
        data-testid={user ? 'workspace-indicator-private' : 'workspace-indicator-public'}
      >
        {user ? <Lock size={13} /> : <Globe size={13} />}
        {user ? 'Signed In — Private Workspace' : 'Guest Mode — Private Workspace'}
      </div>,
      <div key="sep-status" className="tb-menu-sep" role="separator" />
    );
  }
  if (!notebookActionsInBar) {
    if (onClearAllOutputs) {
      moreItems.push(
        <MenuItem key="clear" testId="clear-outputs-btn" icon={<Eraser size={15} />} onClick={() => { closeMenus(); onClearAllOutputs(); }}>
          Clear Outputs
        </MenuItem>
      );
    }
    moreItems.push(
      <MenuItem key="save" testId="save-btn" icon={<Save size={15} />} hint="Ctrl+S" onClick={() => { closeMenus(); onSave(); }}>
        Save
      </MenuItem>
    );
  }
  if (!workspaceToolsInBar) {
    if (moreItems.length) moreItems.push(<div key="sep-tools" className="tb-menu-sep" role="separator" />);
    if (onOpenNotebooks) {
      moreItems.push(
        <MenuItem key="notebooks" testId="navbar-notebooks-btn" icon={<BookOpen size={15} />} onClick={() => { closeMenus(); onOpenNotebooks(); }}>
          Notebooks
        </MenuItem>
      );
    }
    if (onOpenSecrets) {
      moreItems.push(
        <MenuItem key="secrets" testId="navbar-secrets-btn" icon={<Key size={15} />} onClick={() => { closeMenus(); onOpenSecrets(); }}>
          Secrets
        </MenuItem>
      );
    }
    moreItems.push(
      <a
        key="help"
        className="tb-menu-item"
        role="menuitem"
        href={HELP_URL}
        target="_blank"
        rel="noopener noreferrer"
        data-testid="navbar-help-btn"
        onClick={closeMenus}
      >
        <HelpCircle size={15} />
        <span className="tb-menu-item-label">Help</span>
        <span className="tb-menu-item-hint">New tab</span>
      </a>
    );
  }

  if (!themeInBar) {
    moreItems.push(
      <div key="sep-theme" className="tb-menu-sep" role="separator" />,
      <div key="theme-heading" className="tb-menu-heading">
        Theme
      </div>,
      ...themeOptions
    );
  }

  const kernelTone = KERNEL_TONE[kernelStatus] ?? 'info';
  const kernelText = `Python 3 (${kernelStatus})`;

  return (
    <header ref={headerRef} className={`pcs-topbar pcs-topbar--${tier}`} data-tier={tier}>
      {/* Left: panels, brand, notebook title and save state */}
      <div className="tb-section tb-section--start">
        <button
          type="button"
          className={`tb-btn tb-btn--icon tb-btn--touch${isLeftSidebarOpen ? ' is-active' : ''}`}
          onClick={onToggleLeftSidebar}
          aria-label={isLeftSidebarOpen ? 'Collapse Left Sidebar' : 'Expand Left Sidebar'}
          aria-pressed={isLeftSidebarOpen}
          data-tip={`${isLeftSidebarOpen ? 'Hide' : 'Show'} Files sidebar (Ctrl+B)`}
          data-tip-align="start"
          data-testid="left-sidebar-toggle"
        >
          {isLeftSidebarOpen ? <PanelLeftClose size={17} /> : <PanelLeft size={17} />}
        </button>

        {showBrand && (
          <div className="tb-brand" aria-hidden="true">
            <Terminal size={17} />
          </div>
        )}

        <div className="tb-title">
          {showSaveState && (
            <div className="tb-title-meta">
              <span className="tb-app-name">Cloud Studio</span>
              <span className={`tb-save-state${isSaving ? ' is-saving' : ''}`} role="status" aria-live="polite">
                {isSaving ? (
                  <>
                    <Loader2 size={11} className="animate-spin" /> Saving…
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={11} /> Saved
                  </>
                )}
              </span>
            </div>
          )}
          <input
            type="text"
            className="tb-title-input"
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
            aria-label="Notebook title"
            spellCheck={false}
          />
        </div>
      </div>

      {/* Center: execution and notebook actions */}
      <div className="tb-section tb-section--center">
        <div className="tb-group" role="group" aria-label="Run">
          <button
            type="button"
            className="tb-btn tb-btn--primary"
            onClick={onRunAll}
            disabled={isRestarting}
            aria-label="Run All Cells"
            data-tip="Run all cells"
            data-testid="run-all-btn"
          >
            <Play size={14} fill="currentColor" />
            {runLabels && <span>Run All</span>}
          </button>
          <button
            type="button"
            className={`tb-btn${isExecuting ? ' tb-btn--danger-active' : ''}`}
            onClick={onInterruptKernel}
            aria-label="Stop execution"
            data-tip={isExecuting ? 'Stop running code (Ctrl+C)' : 'Stop execution (Ctrl+C while running)'}
            data-testid="stop-execution-btn"
          >
            <Square size={13} className="tb-stop-icon" fill={isExecuting ? 'currentColor' : 'none'} />
            {runLabels && <span>Stop</span>}
          </button>
          <button
            type="button"
            className="tb-btn"
            onClick={onRestartKernel}
            disabled={isRestarting}
            aria-label={isRestarting ? 'Restarting Python Kernel' : 'Restart Python Kernel'}
            aria-busy={isRestarting}
            data-tip={isRestarting ? 'Restarting the Python kernel…' : 'Restart kernel (clears all variables)'}
            data-testid="navbar-restart-btn"
          >
            <RotateCcw size={14} className={isRestarting ? 'animate-spin' : ''} />
            {runLabels && <span>{isRestarting ? 'Restarting…' : 'Restart'}</span>}
          </button>
        </div>

        {notebookActionsInBar && (
          <div className="tb-group" role="group" aria-label="Notebook">
            {onClearAllOutputs && (
              <button
                type="button"
                className="tb-btn"
                onClick={onClearAllOutputs}
                aria-label="Clear Outputs"
                data-tip="Clear all cell outputs (does not stop running code)"
                data-testid="clear-outputs-btn"
              >
                <Eraser size={14} />
                {notebookActionLabels && <span>Clear Outputs</span>}
              </button>
            )}
            <button
              type="button"
              className="tb-btn"
              onClick={onSave}
              aria-label="Save Notebook"
              aria-busy={isSaving}
              data-tip="Save notebook (Ctrl+S)"
              data-testid="save-btn"
            >
              {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              {notebookActionLabels && <span>Save</span>}
            </button>
          </div>
        )}

        {workspaceToolsInBar && (
          <div className="tb-group" role="group" aria-label="Workspace">
            {onOpenNotebooks && (
              <button
                type="button"
                className="tb-btn tb-btn--quiet"
                onClick={onOpenNotebooks}
                aria-label="Notebooks"
                data-tip="Manage workspace notebooks"
                data-testid="navbar-notebooks-btn"
              >
                <BookOpen size={14} />
                {workspaceToolLabels && <span>Notebooks</span>}
              </button>
            )}
            {onOpenSecrets && (
              <button
                type="button"
                className="tb-btn tb-btn--quiet"
                onClick={onOpenSecrets}
                aria-label="Secrets"
                data-tip="Workspace secrets & API keys"
                data-testid="navbar-secrets-btn"
              >
                <Key size={14} />
                {workspaceToolLabels && <span>Secrets</span>}
              </button>
            )}
            <a
              className="tb-btn tb-btn--quiet"
              href={HELP_URL}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Help (opens the user guide in a new tab)"
              data-tip="User guide (new tab)"
              data-testid="navbar-help-btn"
            >
              <HelpCircle size={14} />
              {workspaceToolLabels && <span>Help</span>}
            </a>
          </div>
        )}

        {moreItems.length > 0 && (
          <div className="tb-popover-anchor" ref={moreRef}>
            <button
              type="button"
              className={`tb-btn tb-btn--icon${openMenu === 'more' ? ' is-active' : ''}`}
              onClick={() => toggleMenu('more')}
              aria-label="More actions"
              aria-haspopup="menu"
              aria-expanded={openMenu === 'more'}
              data-tip={openMenu === 'more' ? undefined : 'More actions'}
              data-testid="navbar-more-btn"
            >
              <MoreHorizontal size={17} />
            </button>
            {openMenu === 'more' && (
              <div className="tb-menu tb-menu--start" role="menu" aria-label="More actions" data-testid="navbar-more-menu">
                {moreItems}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right: status, account, appearance, right panel */}
      <div className="tb-section tb-section--end">
        <div
          className={`tb-chip tb-chip--${kernelTone}${kernelLabel ? '' : ' tb-chip--dot-only'}`}
          role="status"
          aria-label={kernelText}
          data-tip={kernelLabel ? undefined : kernelText}
          data-tip-align="end"
          data-testid="kernel-status"
          data-status={kernelStatus}
        >
          <span className={`tb-dot${kernelStatus === 'busy' || kernelStatus === 'restarting' || kernelStatus === 'connecting' ? ' is-pulsing' : ''}`} />
          {kernelLabel && <span className="tb-chip-label">{kernelText}</span>}
        </div>

        {!statusChipsInBar ? null : user ? (
          <div
            className={`tb-chip tb-chip--success${workspaceLabel ? '' : ' tb-chip--icon-only'}`}
            data-testid="workspace-indicator-private"
            data-tip="Private workspace: your files are only visible to you"
            data-tip-align="end"
          >
            <Lock size={12} />
            {workspaceLabelFull ? (
              <span className="tb-chip-label">Signed In — Private Workspace</span>
            ) : (
              <>
                {workspaceLabel && <span className="tb-chip-label" aria-hidden="true">Private</span>}
                <span className="pcs-sr-only">Signed In — Private Workspace</span>
              </>
            )}
          </div>
        ) : (
          <div
            className={`tb-chip tb-chip--info${workspaceLabel ? '' : ' tb-chip--icon-only'}`}
            data-testid="workspace-indicator-public"
            data-tip="Guest mode: your work is private and saved in this browser. Sign in to use it on other devices"
            data-tip-align="end"
          >
            <Globe size={12} />
            {workspaceLabelFull ? (
              <span className="tb-chip-label">Guest Mode — Private Workspace</span>
            ) : (
              <>
                {workspaceLabel && <span className="tb-chip-label" aria-hidden="true">Guest · Private</span>}
                <span className="pcs-sr-only">Guest Mode — Private Workspace</span>
              </>
            )}
          </div>
        )}

        {adminInBar && (
          <button
            type="button"
            className="tb-btn tb-btn--admin"
            onClick={onOpenAdminDashboard}
            aria-label="Admin Console"
            data-tip="Open Super Admin Console"
            data-tip-align="end"
            data-testid="admin-panel-btn"
          >
            <ShieldCheck size={14} />
            {atLeast('lg') && <span>Admin</span>}
          </button>
        )}

        {user ? (
          <div className="tb-popover-anchor" ref={accountRef}>
            <button
              type="button"
              className={`tb-btn tb-btn--account${openMenu === 'account' ? ' is-active' : ''}`}
              onClick={() => toggleMenu('account')}
              aria-label={`Account: ${user.full_name || user.email}`}
              aria-haspopup="menu"
              aria-expanded={openMenu === 'account'}
              data-tip={openMenu === 'account' ? undefined : user.email}
              data-tip-align="end"
              data-testid="account-menu-btn"
            >
              <span className="tb-avatar" aria-hidden="true">
                {initialsOf(user.full_name || '', user.email)}
              </span>
              {atLeast('xl') && <span className="tb-account-name">{user.full_name}</span>}
              <ChevronDown size={13} className="tb-chevron" />
            </button>
            {openMenu === 'account' && (
              <div className="tb-menu tb-menu--end" role="menu" aria-label="Account" data-testid="account-menu">
                <div className="tb-menu-header">
                  <span className="tb-avatar tb-avatar--lg" aria-hidden="true">
                    {initialsOf(user.full_name || '', user.email)}
                  </span>
                  <div className="tb-menu-header-text">
                    <div className="tb-menu-header-name">{user.full_name}</div>
                    <div className="tb-menu-header-email">{user.email}</div>
                    <div className="tb-menu-header-role">{user.role.replace(/_/g, ' ')}</div>
                  </div>
                </div>
                <div className="tb-menu-sep" role="separator" />
                {isAdmin && !adminInBar && (
                  <MenuItem
                    testId="admin-panel-btn"
                    icon={<ShieldCheck size={15} />}
                    onClick={() => {
                      closeMenus();
                      onOpenAdminDashboard?.();
                    }}
                  >
                    Admin Console
                  </MenuItem>
                )}
                <MenuItem
                  testId="signout-btn"
                  icon={<LogOut size={15} />}
                  danger
                  onClick={() => {
                    closeMenus();
                    onLogout();
                  }}
                >
                  Sign out
                </MenuItem>
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            className="tb-btn tb-btn--primary"
            onClick={onOpenAuthModal}
            aria-label="Sign In"
            data-tip="Sign in for a private workspace"
            data-tip-align="end"
            data-testid="signin-button"
          >
            <LogIn size={14} />
            {atLeast('sm') && <span>Sign In</span>}
          </button>
        )}

        {themeInBar && (
          <div className="tb-popover-anchor" ref={themeRef}>
            <button
              type="button"
              id="theme-switcher-btn"
              className={`tb-btn${atLeast('xl') ? '' : ' tb-btn--icon'}${openMenu === 'theme' ? ' is-active' : ''}`}
              onClick={() => toggleMenu('theme')}
              aria-label={`Theme: ${themeMode} (click to change)`}
              aria-haspopup="menu"
              aria-expanded={openMenu === 'theme'}
              data-tip={openMenu === 'theme' ? undefined : `Theme: ${themeMode}`}
              data-tip-align="end"
              data-testid="theme-toggle-btn"
            >
              {themeMode === 'system' ? <Laptop size={15} /> : themeMode === 'light' ? <Sun size={15} /> : <Moon size={15} />}
              {atLeast('xl') && <span style={{ textTransform: 'capitalize' }}>{themeMode}</span>}
            </button>
            {openMenu === 'theme' && (
              <div className="tb-menu tb-menu--end" role="menu" aria-label="Theme" data-testid="theme-dropdown-menu">
                {themeOptions}
              </div>
            )}
          </div>
        )}

        <button
          type="button"
          className={`tb-btn tb-btn--icon tb-btn--touch${isRightSidebarOpen ? ' is-active' : ''}`}
          onClick={onToggleRightSidebar}
          aria-label={isRightSidebarOpen ? 'Collapse File Editor' : 'Expand File Editor'}
          aria-pressed={isRightSidebarOpen}
          data-tip={isRightSidebarOpen ? 'Hide file editor panel' : 'Show file editor panel'}
          data-tip-align="end"
          data-testid="right-panel-toggle"
        >
          {isRightSidebarOpen ? <PanelRightClose size={17} /> : <PanelRight size={17} />}
        </button>
      </div>
    </header>
  );
};

interface MenuItemProps {
  icon: React.ReactNode;
  children: React.ReactNode;
  onClick: () => void;
  testId?: string;
  hint?: string;
  danger?: boolean;
  selected?: boolean;
}

const MenuItem: React.FC<MenuItemProps> = ({ icon, children, onClick, testId, hint, danger, selected }) => (
  <button
    type="button"
    role={selected === undefined ? 'menuitem' : 'menuitemradio'}
    aria-checked={selected}
    className={`tb-menu-item${danger ? ' is-danger' : ''}${selected ? ' is-selected' : ''}`}
    onClick={onClick}
    data-testid={testId}
  >
    {icon}
    <span className="tb-menu-item-label">{children}</span>
    {hint && <span className="tb-menu-item-hint">{hint}</span>}
  </button>
);
